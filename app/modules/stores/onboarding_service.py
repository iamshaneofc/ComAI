"""
Shopify store onboarding — persist credentials, queue product sync + default chat agent.
"""
from __future__ import annotations

import structlog
from fastapi import Depends
from python_slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.onboarding import ONBOARDING_CONNECTED
from app.models.store import Store
from app.repositories.store_repo import StoreRepository
from app.schemas.store import StoreCreatedResponse, StoreOnboardRequest, StoreOnboardResponse
from app.tasks.onboarding_tasks import complete_store_onboarding

logger = structlog.get_logger(__name__)


def _display_name_from_domain(domain: str, explicit_name: str | None) -> str:
    if explicit_name and explicit_name.strip():
        return explicit_name.strip()
    stem = domain.strip().lower().split(".")[0]
    label = stem.replace("-", " ").title() or "Shop"
    return f"{label} Store"


async def _allocate_slug(repo: StoreRepository, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while await repo.get_by_slug(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class StoreOnboardingService:
    """Creates or reconnects a Shopify-backed store and queues post-connect automation."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.repo = StoreRepository(db)

    async def onboard_shopify(self, payload: StoreOnboardRequest) -> StoreOnboardResponse:
        domain = payload.domain.strip().lower()
        token = payload.token.strip()

        existing = await self.repo.get_by_domain(domain)
        if existing:
            creds = dict(existing.credentials or {})
            shop = dict(creds.get("shopify") or {})
            shop["domain"] = domain
            shop["access_token"] = token
            creds["shopify"] = shop
            store = await self.repo.update_store(
                existing,
                {
                    "credentials": creds,
                    "platform": "shopify",
                    "onboarding_status": ONBOARDING_CONNECTED,
                },
            )
            logger.info("Store Shopify credentials refreshed", store_id=str(store.id), domain=domain)
        else:
            name = _display_name_from_domain(domain, payload.name)
            base_slug = slugify(name)
            slug = await _allocate_slug(self.repo, base_slug)
            creds = {"shopify": {"domain": domain, "access_token": token}}
            store = Store(
                name=name,
                slug=slug,
                platform="shopify",
                credentials=creds,
                onboarding_status=ONBOARDING_CONNECTED,
            )
            store = await self.repo.create_store(store)
            logger.info("Store onboarded (new)", store_id=str(store.id), slug=slug, domain=domain)

        complete_store_onboarding.delay(
            str(store.id),
            payload.tone,
            payload.industry_hint,
        )

        base = StoreCreatedResponse.model_validate(store)
        return StoreOnboardResponse(**base.model_dump(), onboarding_job="queued")
