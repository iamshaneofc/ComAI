"""Synchronous Redis client for Celery workers (async redis is not used in sync tasks)."""

from __future__ import annotations

import redis

from app.core.config import settings

_sync_redis: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _sync_redis
