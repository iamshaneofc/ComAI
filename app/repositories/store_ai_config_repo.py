"""
Store AI configuration — one row per tenant.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store_ai_config import StoreAIConfig
from app.repositories.base import BaseRepository


class StoreAIConfigRepository(BaseRepository[StoreAIConfig]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=StoreAIConfig, db=db)

    async def get_by_store_id(self, store_id: UUID) -> StoreAIConfig | None:
        result = await self.db.execute(
            select(StoreAIConfig).where(StoreAIConfig.store_id == store_id)
        )
        return result.scalar_one_or_none()
