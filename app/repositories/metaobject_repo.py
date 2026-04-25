from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metaobject import MetaObject
from app.repositories.base import BaseRepository


class MetaObjectRepository(BaseRepository[MetaObject]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=MetaObject, db=db)

    async def upsert_bulk(self, rows: list[MetaObject]) -> None:
        if not rows:
            return
        values = [{"id": r.id, "store_id": r.store_id, "key": r.key, "value": r.value} for r in rows]
        stmt = insert(MetaObject).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["store_id", "key"],
            set_={"value": stmt.excluded.value, "updated_at": stmt.excluded.updated_at},
        )
        await self.db.execute(stmt)

    async def list_for_store(self, store_id: UUID, *, limit: int = 40) -> list[MetaObject]:
        result = await self.db.execute(
            select(MetaObject)
            .where(MetaObject.store_id == store_id)
            .order_by(MetaObject.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def clear_store(self, store_id: UUID) -> None:
        await self.db.execute(delete(MetaObject).where(MetaObject.store_id == store_id))
