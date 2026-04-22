"""Shared exponential backoff with jitter for Celery manual retries."""

from __future__ import annotations

import random


def retry_countdown_seconds(
    attempt: int,
    *,
    base_seconds: int = 4,
    max_seconds: int = 600,
    jitter_ratio: float = 0.1,
) -> int:
    """
    attempt: Celery ``request.retries`` (0 on first failure, before the next run).

    Returns seconds until the next retry, capped and jittered to avoid thundering herds.
    """
    exp = min(max_seconds, base_seconds * (2**attempt))
    jitter_span = min(30.0, max(1.0, exp * jitter_ratio))
    return int(exp + random.uniform(0, jitter_span))
