"""
Store Service — business logic for store (tenant) management.

Rules:
    - All store business logic lives here
    - Calls StoreRepository for DB access (never raw SQL)
    - Raises HTTPException for user-facing errors
    - Does NOT format HTTP responses (that's the API layer)
"""
import structlog
from fastapi import Depends, HTTPException, status
from python_slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.adapters.shopify.sync import fetch_and_normalize_products
from app.core.database import get_db
from app.core.onboarding import (
    ALLOWED_ONBOARDING_STATUSES,
    ONBOARDING_CREATED,
)
from app.models.store import Store
from app.modules.products.service import ProductService
from app.repositories.agent_repo import AgentRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.store_repo import StoreRepository
from app.schemas.store import StoreCreate, StoreMeStatusResponse, StoreUpdate

logger = structlog.get_logger(__name__)


def _initial_credentials(data: StoreCreate) -> dict | None:
    """Platform-specific secrets live under credentials (e.g. credentials.shopify.domain)."""
    if not data.domain:
        return None
    domain_norm = data.domain.strip().lower()
    creds: dict = {}
    if data.platform == "shopify":
        creds["shopify"] = {"domain": domain_norm}
    else:
        creds[data.platform] = {"domain": domain_norm}
    return creds


class StoreService:
    """Orchestrates all store operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.repo = StoreRepository(db)

    # ----------------------------------------------------------------
    # Create
    # ----------------------------------------------------------------

    async def create_store(self, data: StoreCreate) -> Store:
        """
        Creates a new store (tenant).

        Business rules:
            - Slug is auto-generated from name (unique)
            - Duplicate slugs get a numeric suffix
            - Shopify/custom domain is stored only under credentials
        """
        base_slug = slugify(data.name)

        slug = base_slug
        counter = 1
        while await self.repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        credentials = _initial_credentials(data)

        store = Store(
            name=data.name,
            slug=slug,
            platform=data.platform,
            whatsapp_phone_number=data.whatsapp_phone_number,
            credentials=credentials,
            onboarding_status=ONBOARDING_CREATED,
        )

        created = await self.repo.create_store(store)
        logger.info("Store created", store_id=str(created.id), slug=slug)
        return created

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    async def get_store(self, store_id) -> Store:
        """Fetch a store by UUID. Raises 404 if not found."""
        store = await self.repo.get_by_id(store_id)
        if store is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store {store_id} not found",
            )
        return store

    async def list_stores(
        self,
        offset: int = 0,
        limit: int = 20,
        active_only: bool = True,
    ) -> tuple[list[Store], int]:
        """Returns paginated stores with total count."""
        return await self.repo.list_stores(
            offset=offset, limit=limit, active_only=active_only
        )

    # ----------------------------------------------------------------
    # Update
    # ----------------------------------------------------------------

    async def update_store(self, store_id, data: StoreUpdate) -> Store:
        """Partial update — only provided fields are changed."""
        store = await self.get_store(store_id)
        raw = data.model_dump(exclude_none=True)
        updates: dict = {}

        if "domain" in raw:
            domain = raw.pop("domain")
            creds = dict(store.credentials or {})
            if store.platform == "shopify":
                shop = dict(creds.get("shopify") or {})
                if domain is not None:
                    shop["domain"] = str(domain).strip().lower()
                creds["shopify"] = shop
            else:
                plat = dict(creds.get(store.platform) or {})
                if domain is not None:
                    plat["domain"] = str(domain).strip().lower()
                creds[store.platform] = plat
            updates["credentials"] = creds

        for column in ("name", "whatsapp_phone_number", "is_active"):
            if column in raw:
                updates[column] = raw[column]

        if not updates:
            return store
        updated = await self.repo.update_store(store, updates)
        logger.info("Store updated", store_id=str(store_id), fields=list(updates.keys()))
        return updated

    # ----------------------------------------------------------------
    # Deactivate (soft delete)
    # ----------------------------------------------------------------

    async def deactivate_store(self, store_id) -> Store:
        """Soft-deletes a store by marking is_active=False."""
        store = await self.get_store(store_id)
        deactivated = await self.repo.deactivate_store(store)
        logger.info("Store deactivated", store_id=str(store_id))
        return deactivated

    # ----------------------------------------------------------------
    # Sync Orchestration
    # ----------------------------------------------------------------

    async def sync_store_products(self, store_id) -> int:
        """Full synchronization pipeline. Orchestrated via the service layer."""
        structlog.contextvars.bind_contextvars(flow="sync", store_id=str(store_id))
        store = await self.get_store(store_id)
        creds = store.credentials.get("shopify", {}) if store.credentials else {}
        domain = creds.get("domain")
        access_token = creds.get("access_token")

        if not domain or not access_token:
            logger.error("Shopify credentials missing for store", store_id=str(store_id))
            return 0

        product_service = ProductService(self.db)
        total_synced = 0

        async for normalized_products in fetch_and_normalize_products(store_id, domain, access_token):
            await product_service.bulk_upsert_products(store_id, normalized_products)
            await self.db.commit()
            total_synced += len(normalized_products)

        return total_synced

    # ----------------------------------------------------------------
    # Onboarding status
    # ----------------------------------------------------------------

    async def update_onboarding_status(self, store_id: UUID, status: str) -> None:
        """Persist onboarding lifecycle state (no HTTP semantics)."""
        if status not in ALLOWED_ONBOARDING_STATUSES:
            raise ValueError(f"Invalid onboarding_status: {status}")
        store = await self.repo.get_by_id(store_id)
        if store is None:
            logger.warning("update_onboarding_status: store not found", store_id=str(store_id))
            return
        await self.repo.update_store(store, {"onboarding_status": status})

    async def get_me_onboarding_status(self, store_id: UUID) -> StoreMeStatusResponse:
        """Aggregate progress for GET /stores/me/status."""
        store = await self.get_store(store_id)
        products = ProductRepository(self.db)
        agents = AgentRepository(self.db)
        products_count = await products.count_for_store(store_id)
        chat_agent = await agents.get_by_type(store_id, "chat")
        return StoreMeStatusResponse(
            onboarding_status=store.onboarding_status,  # type: ignore[arg-type]
            products_count=products_count,
            agent_ready=chat_agent is not None,
        )
