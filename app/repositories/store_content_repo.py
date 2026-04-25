from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store_content import StoreContent
from app.repositories.base import BaseRepository


class StoreContentRepository(BaseRepository[StoreContent]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=StoreContent, db=db)

    async def upsert_bulk(self, rows: list[StoreContent]) -> None:
        if not rows:
            return
        values = [
            {
                "id": r.id,
                "store_id": r.store_id,
                "type": r.type,
                "title": r.title,
                "body": r.body,
                "metadata": r.metadata,
                "external_id": r.external_id,
            }
            for r in rows
        ]
        stmt = insert(StoreContent).values(values)
        update_dict = {
            c.name: c
            for c in stmt.excluded
            if c.name not in ("id", "store_id", "external_id", "created_at")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["store_id", "external_id"],
            set_=update_dict,
        )
        await self.db.execute(stmt)

    async def list_for_store(self, store_id: UUID, *, limit: int = 30) -> list[StoreContent]:
        result = await self.db.execute(
            select(StoreContent)
            .where(StoreContent.store_id == store_id)
            .order_by(StoreContent.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_types(
        self,
        store_id: UUID,
        types: list[str],
        *,
        limit: int = 20,
    ) -> list[StoreContent]:
        result = await self.db.execute(
            select(StoreContent)
            .where(StoreContent.store_id == store_id, StoreContent.type.in_(types))
            .order_by(StoreContent.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def clear_store(self, store_id: UUID) -> None:
        await self.db.execute(delete(StoreContent).where(StoreContent.store_id == store_id))
