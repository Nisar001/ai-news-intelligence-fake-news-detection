from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.repositories.article_repo import create_article, create_job
from app.schemas.analysis import AnalyzeAcceptedResponse, AnalyzeRequest
from app.services.input_service import sanitize_input, validate_text_length
from app.services.nlp_pipeline import process_text
from app.services.scrape_service import fetch_article_from_url
from app.tasks.workers import run_analysis_task

router = APIRouter(prefix="/analyze")


@router.post("", response_model=AnalyzeAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_article(
    payload: AnalyzeRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_api_key),
) -> AnalyzeAcceptedResponse:
    source_url = None
    title = None

    if payload.text:
        text = payload.text
    else:
        fetched = await fetch_article_from_url(str(payload.url))
        source_url = fetched["source_url"]
        title = fetched["title"]
        text = fetched["text"]

    sanitized = sanitize_input(text)
    validate_text_length(sanitized)
    nlp_preview = process_text(sanitized)

    article = await create_article(
        db=db,
        raw_text=text,
        cleaned_text=nlp_preview["cleaned_text"],
        source_url=source_url,
        title=title,
        metadata_json={"feature_vector": nlp_preview["feature_vector"]},
    )
    job = await create_job(db=db, article_id=article.id)
    await db.commit()

    run_analysis_task.delay(str(job.id))
    return AnalyzeAcceptedResponse(job_id=job.id, article_id=article.id)
