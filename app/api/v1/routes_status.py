from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db_session
from app.repositories.article_repo import get_job
from app.schemas.analysis import JobStatusResponse

router = APIRouter(prefix="/status")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_api_key),
) -> JobStatusResponse:
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        classification=job.classification,
        confidence=job.confidence,
        processing_ms=job.processing_ms,
        error_message=job.error_message,
    )
