from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalysisJob, Article


async def create_article(
    db: AsyncSession,
    raw_text: str,
    cleaned_text: str,
    source_url: str | None,
    title: str | None,
    metadata_json: dict,
) -> Article:
    article = Article(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        source_url=source_url,
        title=title,
        metadata_json=metadata_json,
    )
    db.add(article)
    await db.flush()
    return article


async def create_job(db: AsyncSession, article_id: UUID, status: str = "PENDING") -> AnalysisJob:
    job = AnalysisJob(article_id=article_id, status=status)
    db.add(job)
    await db.flush()
    return job


async def get_article(db: AsyncSession, article_id: UUID) -> Article | None:
    stmt = select(Article).where(Article.id == article_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_job(db: AsyncSession, job_id: UUID) -> AnalysisJob | None:
    stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_job_for_article(db: AsyncSession, article_id: UUID) -> AnalysisJob | None:
    stmt = select(AnalysisJob).where(AnalysisJob.article_id == article_id).order_by(AnalysisJob.created_at.desc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()
