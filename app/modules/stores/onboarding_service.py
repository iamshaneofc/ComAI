"""
Store onboarding — persist credentials, queue product sync + default chat agent.
"""
from __future__ import annotations

import structlog
from fastapi import Depends
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.shopify.oauth_token_cache import invalidate_shopify_oauth_cache
from app.core.database import get_db
from app.core.field_crypto import encrypt_secret_text
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


def _build_shopify_credentials_block(
    domain: str,
    token: str,
    webhook_secret_plain: str,
    client_id: str,
    client_secret: str,
    previous_shop: dict | None = None,
) -> dict:
    """Merge Shopify JSON under credentials.shopify (domain drives storefront product sync)."""
    shop = dict(previous_shop or {})
    shop["domain"] = domain
    ws = webhook_secret_plain.strip()
    if ws:
        shop["webhook_secret"] = encrypt_secret_text(ws)
    elif previous_shop and previous_shop.get("webhook_secret"):
        shop["webhook_secret"] = previous_shop["webhook_secret"]
    else:
        shop.pop("webhook_secret", None)
    if token:
        shop["access_token"] = encrypt_secret_text(token)
    elif previous_shop and previous_shop.get("access_token"):
        shop["access_token"] = previous_shop["access_token"]
    else:
        shop.pop("access_token", None)
    if client_id and client_secret:
        shop["client_id"] = client_id
        shop["client_secret"] = encrypt_secret_text(client_secret)
    elif previous_shop:
        for k in ("client_id", "client_secret"):
            if k in previous_shop:
                shop[k] = previous_shop[k]
    else:
        shop.pop("client_id", None)
        shop.pop("client_secret", None)
    return shop


class StoreOnboardingService:
    """Creates or reconnects a store and queues post-connect automation."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.repo = StoreRepository(db)

    async def onboard_store(self, payload: StoreOnboardRequest) -> StoreOnboardResponse:
        if payload.platform == "custom":
            return await self._onboard_custom(payload)
        return await self._onboard_shopify(payload)

    async def _onboard_shopify(self, payload: StoreOnboardRequest) -> StoreOnboardResponse:
        domain = payload.domain.strip().lower()
        token = payload.token.strip()
        webhook_secret = payload.webhook_secret.strip()
        client_id = payload.client_id.strip()
        client_secret = payload.client_secret.strip()

        existing = await self.repo.get_by_platform_domain("shopify", domain)
        if existing:
            creds = dict(existing.credentials or {})
            prev_shop = dict(creds.get("shopify") or {})
            shop = _build_shopify_credentials_block(
                domain,
                token,
                webhook_secret,
                client_id,
                client_secret,
                previous_shop=prev_shop,
            )
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
            shop = _build_shopify_credentials_block(
                domain,
                token,
                webhook_secret,
                client_id,
                client_secret,
                previous_shop=None,
            )
            creds = {"shopify": shop}
            store = Store(
                name=name,
                slug=slug,
                platform="shopify",
                credentials=creds,
                onboarding_status=ONBOARDING_CONNECTED,
            )
            store = await self.repo.create_store(store)
            logger.info("Store onboarded (new)", store_id=str(store.id), slug=slug, domain=domain)

        invalidate_shopify_oauth_cache(str(store.id))

        onboarding_job = "queued"
        try:
            complete_store_onboarding.apply_async(
                args=(str(store.id), payload.tone, payload.industry_hint),
                retry=False,
            )
        except Exception as exc:
            onboarding_job = "enqueue_failed"
            logger.error(
                "Onboarding task enqueue failed",
                store_id=str(store.id),
                error=str(exc),
            )

        base = StoreCreatedResponse.model_validate(store)
        return StoreOnboardResponse(**base.model_dump(), onboarding_job=onboarding_job)

    async def _onboard_custom(self, payload: StoreOnboardRequest) -> StoreOnboardResponse:
        domain = payload.domain.strip().lower()
        products_url = payload.custom_products_url.strip()
        items_path = payload.custom_items_path.strip()
        field_map = payload.custom_field_map or {}

        existing = await self.repo.get_by_platform_domain("custom", domain)
        if existing and existing.platform == "custom":
            creds = dict(existing.credentials or {})
            creds["custom"] = {
                "domain": domain,
                "products_url": products_url,
                "items_path": items_path,
                "field_map": field_map,
            }
            store = await self.repo.update_store(
                existing,
                {
                    "credentials": creds,
                    "platform": "custom",
                    "onboarding_status": ONBOARDING_CONNECTED,
                },
            )
            logger.info("Store custom feed refreshed", store_id=str(store.id), domain=domain)
        else:
            name = _display_name_from_domain(domain, payload.name)
            base_slug = slugify(name)
            slug = await _allocate_slug(self.repo, base_slug)
            creds = {
                "custom": {
                    "domain": domain,
                    "products_url": products_url,
                    "items_path": items_path,
                    "field_map": field_map,
                }
            }
            store = Store(
                name=name,
                slug=slug,
                platform="custom",
                credentials=creds,
                onboarding_status=ONBOARDING_CONNECTED,
            )
            store = await self.repo.create_store(store)
            logger.info("Store onboarded (custom)", store_id=str(store.id), slug=slug, domain=domain)

        onboarding_job = "queued"
        try:
            complete_store_onboarding.apply_async(
                args=(str(store.id), payload.tone, payload.industry_hint),
                retry=False,
            )
        except Exception as exc:
            onboarding_job = "enqueue_failed"
            logger.error(
                "Onboarding task enqueue failed",
                store_id=str(store.id),
                error=str(exc),
            )

        base = StoreCreatedResponse.model_validate(store)
        return StoreOnboardResponse(**base.model_dump(), onboarding_job=onboarding_job)
