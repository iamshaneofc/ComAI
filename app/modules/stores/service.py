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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.store import Store
from app.repositories.store_repo import StoreRepository
from app.schemas.store import StoreCreate, StoreUpdate
from app.modules.products.service import ProductService
from app.adapters.shopify.sync import fetch_and_normalize_products

logger = structlog.get_logger(__name__)


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
        """
        base_slug = slugify(data.name)

        # Ensure slug uniqueness
        slug = base_slug
        counter = 1
        while await self.repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        store = Store(
            name=data.name,
            slug=slug,
            platform=data.platform,
            shopify_domain=data.domain,
            whatsapp_phone_number=data.whatsapp_phone_number,
        )

        created = await self.repo.create_store(store)
        logger.info("Store created", store_id=str(created.id), slug=slug)
        return created

    # ----------------------------------------------------------------
    # Read
    # ----------------------------------------------------------------

    async def get_store(self, store_id) -> Store:
        """Fetch a store by UUID. Raises 404 if not found."""
        result = await self.db.execute(
            select(Store).where(Store.id == store_id)
        )
        store = result.scalar_one_or_none()
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
        updates = data.model_dump(exclude_none=True)
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
            logger.error(f"Shopify credentials missing for store {store_id}")
            return 0
            
        product_service = ProductService(self.db)
        total_synced = 0
        
        async for normalized_products in fetch_and_normalize_products(store_id, domain, access_token):
            await product_service.bulk_upsert_products(store_id, normalized_products)
            # Service explicitly controls the transaction boundary here for chunking
            await self.db.commit()
            total_synced += len(normalized_products)
            
        return total_synced
