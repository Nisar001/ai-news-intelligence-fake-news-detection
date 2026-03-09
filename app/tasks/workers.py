from __future__ import annotations

import asyncio
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.repositories.article_repo import get_article, get_job
from app.services.classifier import classify_article
from app.services.explainability import build_reasoning_summary
from app.services.nlp_pipeline import process_text
from app.services.summarizer_gemini import generate_summary
from app.tasks.celery_app import celery_app

_worker_loop: asyncio.AbstractEventLoop | None = None


async def _run_analysis(job_id: UUID) -> None:
    async with SessionLocal() as db:  # type: AsyncSession
        job = await get_job(db, job_id)
        if not job:
            return

        job.status = "PROCESSING"
        await db.commit()

        article = await get_article(db, job.article_id)
        if not article:
            job.status = "FAILED"
            job.error_message = "Article not found"
            await db.commit()
            return

        started = time.perf_counter()
        try:
            nlp = process_text(article.cleaned_text)
            clf = classify_article(article.cleaned_text)
            try:
                summary = generate_summary(
                    article=article.cleaned_text,
                    label=clf["classification"],
                    confidence=clf["confidence"],
                    entities=nlp["entities"],
                    sentiment=nlp["sentiment"],
                )
                summary_error = None
            except Exception as summary_exc:
                summary_error = str(summary_exc)
                summary = {
                    "executive_summary": "Summary unavailable due to LLM quota or provider error.",
                    "detailed_summary": "",
                    "risk_analysis": "LLM-based risk analysis unavailable. Using model and NLP signals only.",
                    "reasoning": "",
                    "suspicious_claims": [],
                    "model": "fallback-no-llm",
                }

            job.status = "COMPLETED"
            job.classification = clf["classification"]
            job.confidence = clf["confidence"]
            job.model_name = clf["model_name"]
            job.summary_executive = summary["executive_summary"]
            job.summary_detailed = summary["detailed_summary"]
            job.risk_analysis = summary["risk_analysis"]
            job.reasoning = summary.get("reasoning") or build_reasoning_summary(
                classification=clf["classification"],
                confidence=clf["confidence"],
                keywords=nlp["important_keywords"],
                sentiment=nlp["sentiment"],
            )
            job.important_keywords = nlp["important_keywords"]
            job.attention_weights = clf.get("attention_weights", {})
            job.entities = nlp["entities"]
            job.sentiment = nlp["sentiment"]
            job.suspicious_claims = summary.get("suspicious_claims", [])
            if summary_error:
                job.error_message = summary_error
            job.processing_ms = int((time.perf_counter() - started) * 1000)
        except Exception as exc:
            job.status = "FAILED"
            job.error_message = str(exc)
            job.processing_ms = int((time.perf_counter() - started) * 1000)

        await db.commit()


@celery_app.task(name="app.tasks.workers.run_analysis_task")
def run_analysis_task(job_id: str) -> None:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_worker_loop)
    _worker_loop.run_until_complete(_run_analysis(UUID(job_id)))
