"""Redis-backed deduplication so the same automation trigger does not fire repeatedly."""

from __future__ import annotations

import hashlib
from uuid import UUID

import structlog

from app.core.redis_client import get_redis

logger = structlog.get_logger(__name__)

DEDUP_KEY_PREFIX = "automation:dedupe:v1"
DEFAULT_TTL_SECONDS = 48 * 3600


def trigger_fingerprint(trigger: dict) -> str:
    """Stable key fragment for a trigger shape (category or product)."""
    ttype = trigger["trigger_type"]
    meta = trigger["metadata"]
    if ttype == "repeated_interest":
        raw = f"ri:{meta.get('category', '')}"
    elif ttype == "high_intent":
        raw = f"hi:{meta.get('product_id', '')}"
    else:
        raw = f"other:{ttype}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _dedup_key(store_id: UUID, user_id: UUID, fingerprint: str) -> str:
    return f"{DEDUP_KEY_PREFIX}:{store_id}:{user_id}:{fingerprint}"


async def try_acquire_trigger_slot(
    store_id: UUID,
    user_id: UUID,
    trigger: dict,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> tuple[bool, str]:
    """
    Attempt to reserve this trigger for a single automation run.

    Returns (acquired, fingerprint). If Redis errors, returns (True, fp) so automation still runs.
    """
    fp = trigger_fingerprint(trigger)
    key = _dedup_key(store_id, user_id, fp)
    try:
        r = await get_redis()
        acquired = bool(await r.set(key, "1", nx=True, ex=ttl_seconds))
        return acquired, fp
    except Exception as exc:
        logger.warning(
            "automation_dedup_redis_failed",
            error=str(exc),
            store_id=str(store_id),
            user_id=str(user_id),
        )
        return True, fp


async def release_trigger_slot(store_id: UUID, user_id: UUID, fingerprint: str) -> None:
    """Remove reservation so a failed run can be retried."""
    key = _dedup_key(store_id, user_id, fingerprint)
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as exc:
        logger.warning(
            "automation_dedup_release_failed",
            error=str(exc),
            store_id=str(store_id),
            user_id=str(user_id),
        )
