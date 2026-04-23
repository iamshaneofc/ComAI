"""Celery tasks — store onboarding: product sync then default chat agent with generated system prompt."""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import update

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.onboarding import ONBOARDING_FAILED, ONBOARDING_READY, ONBOARDING_SYNCING
from app.models.agent import Agent
from app.modules.stores.service import StoreService
from app.repositories.agent_repo import AgentRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.store_repo import StoreRepository
from app.services.prompt_generator_service import PromptGeneratorService
from app.tasks.task_logging import log_task_failed, log_task_started, log_task_succeeded

MAX_RETRIES = 3

logger = structlog.get_logger(__name__)

# Onboard API uses friendly|professional|playful; Agent rows use friendly|premium|aggressive.
_ONBOARD_TO_AGENT_TONE = {"friendly": "friendly", "professional": "premium", "playful": "aggressive"}


async def _persist_onboarding_failed(store_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        svc = StoreService(db=session)
        await svc.update_onboarding_status(store_id, ONBOARDING_FAILED)
        await session.commit()


async def _complete_onboarding_async(
    store_id: UUID,
    tone: str,
    industry_hint: str | None,
) -> None:
    async with AsyncSessionLocal() as session:
        store_repo = StoreRepository(session)
        store = await store_repo.get_by_id(store_id)
        if store is None:
            logger.error("Onboarding aborted: store not found", store_id=str(store_id))
            return

        store_service = StoreService(db=session)
        await store_service.update_onboarding_status(store_id, ONBOARDING_SYNCING)
        await session.commit()

        synced = await store_service.sync_store_products(store_id)
        logger.info("Onboarding sync finished", store_id=str(store_id), products_synced=synced)

        products = ProductRepository(session)
        categories = await products.sample_product_categories(store_id)

        agent_tone = _ONBOARD_TO_AGENT_TONE.get(tone, "friendly")
        prompt = PromptGeneratorService.build_chat_system_prompt(
            store_name=store.name,
            product_categories=categories,
            tone=agent_tone,
            industry_hint=industry_hint,
            goal="sales",
            language=None,
        )

        await session.execute(
            update(Agent)
            .where(
                Agent.store_id == store_id,
                Agent.type == "chat",
            )
            .values(is_active=False)
        )
        await session.flush()

        agent = Agent(
            store_id=store_id,
            name="Shop Assistant",
            type="chat",
            model="gpt-4o",
            system_prompt=prompt,
            temperature=0.7,
            is_active=True,
            tone=agent_tone,
            goal="sales",
            language=None,
        )
        session.add(agent)
        await session.flush()
        await AgentRepository(session).deactivate_others_same_type(store_id, "chat", agent.id)

        await store_service.update_onboarding_status(store_id, ONBOARDING_READY)
        await session.commit()
        logger.info(
            "Default chat agent ready",
            store_id=str(store_id),
            agent_id=str(agent.id),
            categories_used=len(categories),
        )


@celery_app.task(bind=True, max_retries=MAX_RETRIES, acks_late=True)
def complete_store_onboarding(
    self,
    store_id: str,
    tone: str = "friendly",
    industry_hint: str | None = None,
) -> None:
    task_name = self.name
    task_id = self.request.id
    log_task_started(task_name, task_id=task_id, idempotency_key=None, store_id=store_id)

    try:
        asyncio.run(_complete_onboarding_async(UUID(store_id), tone, industry_hint))
    except Exception as exc:
        will_retry = self.request.retries < self.max_retries
        log_task_failed(
            task_name,
            task_id=task_id,
            idempotency_key=None,
            exc=exc,
            will_retry=will_retry,
            store_id=store_id,
        )
        if not will_retry:
            try:
                asyncio.run(_persist_onboarding_failed(UUID(store_id)))
            except Exception as mark_exc:
                logger.error(
                    "Could not persist onboarding failed status",
                    store_id=store_id,
                    error=str(mark_exc),
                )
        if will_retry:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1)) from exc
        raise

    log_task_succeeded(task_name, task_id=task_id, idempotency_key=None, store_id=store_id)
