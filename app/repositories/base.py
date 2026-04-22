"""
Base Repository — generic CRUD operations for all domain repositories.

Rules:
    - ALL database access goes through a repository
    - Every method receives store_id for multi-tenancy enforcement
    - No business logic — pure data access
    - Services call repositories; repositories NEVER call services
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async CRUD base. Domain repos inherit and extend."""

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get_by_id(self, id: UUID, store_id: UUID) -> ModelType | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.store_id == store_id,  # type: ignore[attr-defined]
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        store_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        result = await self.db.execute(
            select(self.model)
            .where(self.model.store_id == store_id)  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()  # Get ID without committing (session handles commit)
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, updates: dict[str, Any]) -> ModelType:
        for key, value in updates.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.flush()
