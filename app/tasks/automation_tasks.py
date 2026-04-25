"""Celery tasks for automation — fresh DB session per run, explicit commit/rollback."""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from app.core.celery_app import celery_app
from app.core.celery_retry import retry_countdown_seconds
from app.core.database import AsyncSessionLocal
from app.tasks.task_idempotency import TaskIdempotency, stable_idempotency_key
from app.tasks.task_logging import (
    log_task_failed,
    log_task_skipped_idempotent,
    log_task_started,
    log_task_succeeded,
)

MAX_RETRIES = 5
_worker_loop: asyncio.AbstractEventLoop | None = None

logger = structlog.get_logger(__name__)


def _run_on_worker_loop(coro):
    """
    Run async code on a persistent loop in this worker process.

    This avoids asyncpg "Future attached to a different loop" failures on
    Windows/solo workers when tasks are executed repeatedly.
    """
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coro)


async def _evaluate_user_async(store_id: UUID, user_id: UUID, task_id: str | None = None) -> None:
    from app.modules.automation.service import AutomationService
    from app.repositories.user_repo import UserRepository

    async with AsyncSessionLocal() as session:
        try:
            if await UserRepository(session).get_by_id_for_store(store_id, user_id) is None:
                logger.warning("Automation task skipped: user not in tenant", store_id=str(store_id))
                return
            svc = AutomationService(session)
            await svc.evaluate_user(store_id, user_id, task_id=task_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@celery_app.task(bind=True, max_retries=MAX_RETRIES, acks_late=True)
def evaluate_user_automation(
    self,
    store_id: str,
    user_id: str,
    idempotency_key: str | None = None,
) -> None:
    raw_key = stable_idempotency_key(str(store_id), str(user_id), explicit=idempotency_key)
    idem = TaskIdempotency(namespace="automation.evaluate_user", idempotency_key=raw_key)
    task_name = self.name
    task_id = self.request.id

    outcome = idem.check_or_acquire()
    if outcome == "already_completed":
        log_task_skipped_idempotent(
            task_name,
            task_id=task_id,
            idempotency_key=raw_key,
            reason="already_completed",
            store_id=store_id,
            user_id=user_id,
        )
        return

    log_task_started(
        task_name,
        task_id=task_id,
        idempotency_key=raw_key,
        store_id=store_id,
        user_id=user_id,
    )

    if outcome == "lease_held":
        log_task_skipped_idempotent(
            task_name,
            task_id=task_id,
            idempotency_key=raw_key,
            reason="lease_held_retry",
            store_id=store_id,
            user_id=user_id,
        )
        raise self.retry(
            countdown=retry_countdown_seconds(self.request.retries),
        )

    try:
        _run_on_worker_loop(_evaluate_user_async(UUID(store_id), UUID(user_id), task_id=task_id))
    except Exception as exc:
        idem.release_lease()
        will_retry = self.request.retries < self.max_retries
        log_task_failed(
            task_name,
            task_id=task_id,
            idempotency_key=raw_key,
            exc=exc,
            will_retry=will_retry,
            store_id=store_id,
            user_id=user_id,
        )
        if will_retry:
            raise self.retry(
                exc=exc,
                countdown=retry_countdown_seconds(self.request.retries),
            ) from exc
        raise

    idem.mark_completed()
    log_task_succeeded(
        task_name,
        task_id=task_id,
        idempotency_key=raw_key,
        store_id=store_id,
        user_id=user_id,
    )
