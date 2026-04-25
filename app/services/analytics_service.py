from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.store_analytics_metric_repo import StoreAnalyticsMetricRepository
from app.schemas.analytics import AnalyticsMetric, AnalyticsOverviewResponse


class AnalyticsService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.repo = StoreAnalyticsMetricRepository(db)

    async def upsert_metrics(self, store_id: UUID, metrics: dict[str, dict]) -> None:
        await self.repo.upsert_many(store_id, metrics)
        await self.db.commit()

    async def get_overview(self, store_id: UUID) -> AnalyticsOverviewResponse:
        rows = await self.repo.get_all_for_store(store_id)
        return AnalyticsOverviewResponse(
            items=[
                AnalyticsMetric(key=r.key, value=r.value, updated_at=r.updated_at or datetime.now(UTC))
                for r in rows
            ]
        )
