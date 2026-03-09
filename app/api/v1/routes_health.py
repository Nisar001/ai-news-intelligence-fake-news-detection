from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.cache_service import get_cache_client

router = APIRouter(prefix="/health")


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db_session)) -> dict:
    db_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    cache: Redis = get_cache_client()
    try:
        await cache.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "ok" if db_ok and redis_ok else "degraded"
    return {"status": status, "database": db_ok, "redis": redis_ok}
