from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.repositories.article_repo import get_article, get_latest_job_for_article
from app.schemas.analysis import ArticleResponse

router = APIRouter(prefix="/article")


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_by_id(
    article_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_api_key),
) -> ArticleResponse:
    article = await get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    job = await get_latest_job_for_article(db, article_id)
    latest_job = None
    if job:
        latest_job = {
            "job_id": str(job.id),
            "status": job.status,
            "classification": job.classification,
            "confidence": job.confidence,
            "summary_executive": job.summary_executive,
            "risk_analysis": job.risk_analysis,
            "reasoning": job.reasoning,
            "important_keywords": job.important_keywords,
            "attention_weights": job.attention_weights,
            "entities": job.entities,
            "sentiment": job.sentiment,
            "suspicious_claims": job.suspicious_claims,
            "processing_ms": job.processing_ms,
            "error_message": job.error_message,
        }

    return ArticleResponse(
        article_id=article.id,
        source_url=article.source_url,
        title=article.title,
        raw_text=article.raw_text,
        cleaned_text=article.cleaned_text,
        metadata=article.metadata_json,
        latest_job=latest_job,
    )
