from __future__ import annotations

import json

from redis.asyncio import Redis

from app.core.config import get_settings


def get_cache_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def cache_set(key: str, payload: dict, ttl: int | None = None) -> None:
    settings = get_settings()
    client = get_cache_client()
    await client.set(name=key, value=json.dumps(payload), ex=ttl or settings.cache_ttl_seconds)


async def cache_get(key: str) -> dict | None:
    client = get_cache_client()
    value = await client.get(key)
    return json.loads(value) if value else None
