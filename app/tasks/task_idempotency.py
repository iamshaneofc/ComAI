"""Redis-backed idempotency for Celery tasks (at-least-once delivery, dedupe window)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from app.core.redis_sync import get_sync_redis

IdempotencyOutcome = Literal["proceed", "already_completed", "lease_held"]


def stable_idempotency_key(*parts: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass
class TaskIdempotency:
    """Lease while running; mark completed after success so duplicates no-op."""

    namespace: str
    idempotency_key: str
    lease_ttl_seconds: int = 600
    completed_ttl_seconds: int = 7 * 24 * 3600

    def _keys(self) -> tuple[str, str]:
        h = hashlib.sha256(self.idempotency_key.encode("utf-8")).hexdigest()[:40]
        prefix = f"celery:idem:v1:{self.namespace}"
        return f"{prefix}:done:{h}", f"{prefix}:lease:{h}"

    def check_or_acquire(self) -> IdempotencyOutcome:
        r = get_sync_redis()
        done_key, lease_key = self._keys()
        if r.get(done_key):
            return "already_completed"
        if r.set(lease_key, "1", nx=True, ex=self.lease_ttl_seconds):
            return "proceed"
        if r.get(done_key):
            return "already_completed"
        return "lease_held"

    def mark_completed(self) -> None:
        r = get_sync_redis()
        done_key, lease_key = self._keys()
        pipe = r.pipeline()
        pipe.set(done_key, "1", ex=self.completed_ttl_seconds)
        pipe.delete(lease_key)
        pipe.execute()

    def release_lease(self) -> None:
        r = get_sync_redis()
        _, lease_key = self._keys()
        r.delete(lease_key)
