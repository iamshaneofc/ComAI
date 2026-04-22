"""Structured Celery task lifecycle events (structlog)."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def log_task_started(
    task_name: str,
    *,
    task_id: str,
    idempotency_key: str | None,
    **fields: Any,
) -> None:
    logger.info(
        "celery.task.started",
        celery_task_name=task_name,
        celery_task_id=task_id,
        idempotency_key=idempotency_key,
        **fields,
    )


def log_task_succeeded(
    task_name: str,
    *,
    task_id: str,
    idempotency_key: str | None,
    **fields: Any,
) -> None:
    logger.info(
        "celery.task.succeeded",
        celery_task_name=task_name,
        celery_task_id=task_id,
        idempotency_key=idempotency_key,
        **fields,
    )


def log_task_failed(
    task_name: str,
    *,
    task_id: str,
    idempotency_key: str | None,
    exc: BaseException,
    will_retry: bool,
    **fields: Any,
) -> None:
    logger.error(
        "celery.task.failed",
        celery_task_name=task_name,
        celery_task_id=task_id,
        idempotency_key=idempotency_key,
        will_retry=will_retry,
        error_type=type(exc).__name__,
        error=str(exc),
        exc_info=True,
        **fields,
    )


def log_task_skipped_idempotent(
    task_name: str,
    *,
    task_id: str,
    idempotency_key: str | None,
    reason: str,
    **fields: Any,
) -> None:
    logger.info(
        "celery.task.skipped_idempotent",
        celery_task_name=task_name,
        celery_task_id=task_id,
        idempotency_key=idempotency_key,
        reason=reason,
        **fields,
    )
