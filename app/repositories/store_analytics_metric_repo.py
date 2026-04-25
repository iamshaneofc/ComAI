from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store_analytics_metric import StoreAnalyticsMetric
from app.repositories.base import BaseRepository


class StoreAnalyticsMetricRepository(BaseRepository[StoreAnalyticsMetric]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=StoreAnalyticsMetric, db=db)

    async def upsert_many(self, store_id: UUID, metrics: dict[str, dict]) -> None:
        if not metrics:
            return
        values = [{"store_id": store_id, "key": k, "value": v} for k, v in metrics.items()]
        stmt = insert(StoreAnalyticsMetric).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["store_id", "key"],
            set_={"value": stmt.excluded.value, "updated_at": stmt.excluded.updated_at},
        )
        await self.db.execute(stmt)

    async def get_all_for_store(self, store_id: UUID) -> list[StoreAnalyticsMetric]:
        result = await self.db.execute(
            select(StoreAnalyticsMetric)
            .where(StoreAnalyticsMetric.store_id == store_id)
            .order_by(StoreAnalyticsMetric.key.asc())
        )
        return list(result.scalars().all())
