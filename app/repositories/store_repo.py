"""
Store Repository — concrete DB queries for the Store (tenant) entity.

Rules:
    - ALL SQL in this file only — no logic, no HTTP calls
    - Every query method is async
    - Returns None on not-found (never raises 404 — that's the service's job)
"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.repositories.base import BaseRepository


class StoreRepository(BaseRepository[Store]):
    """Store-specific data access layer."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Store, db=db)

    # ----------------------------------------------------------------
    # Reads
    # ----------------------------------------------------------------

    async def get_by_slug(self, slug: str) -> Store | None:
        result = await self.db.execute(
            select(Store).where(Store.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Store | None:
        result = await self.db.execute(
            select(Store).where(Store.shopify_domain == domain)
        )
        return result.scalar_one_or_none()

    async def list_stores(
        self,
        offset: int = 0,
        limit: int = 20,
        active_only: bool = True,
    ) -> tuple[list[Store], int]:
        """Returns (stores, total_count) for pagination."""
        q = select(Store)
        count_q = select(func.count()).select_from(Store)

        if active_only:
            q = q.where(Store.is_active.is_(True))
            count_q = count_q.where(Store.is_active.is_(True))

        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        paginated_result = await self.db.execute(q.offset(offset).limit(limit))
        stores = list(paginated_result.scalars().all())

        return stores, total

    # ----------------------------------------------------------------
    # Writes
    # ----------------------------------------------------------------

    async def create_store(self, store: Store) -> Store:
        return await self.create(store)

    async def update_store(self, store: Store, updates: dict) -> Store:
        return await self.update(store, updates)

    async def deactivate_store(self, store: Store) -> Store:
        return await self.update(store, {"is_active": False})
