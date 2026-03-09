from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.repositories.article_repo import create_job, get_article
from app.schemas.analysis import AnalyzeAcceptedResponse, SummarizeRequest
from app.tasks.workers import run_analysis_task

router = APIRouter(prefix="/summarize")


@router.post("", response_model=AnalyzeAcceptedResponse)
async def summarize_article(
    payload: SummarizeRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_api_key),
) -> AnalyzeAcceptedResponse:
    article = await get_article(db, payload.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    job = await create_job(db=db, article_id=article.id)
    await db.commit()
    run_analysis_task.delay(str(job.id))
    return AnalyzeAcceptedResponse(job_id=job.id, article_id=article.id)
