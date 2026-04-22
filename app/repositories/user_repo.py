from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(model=User, db=db)

    async def get_by_external_id(self, store_id: UUID, external_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.store_id == store_id, User.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_store(self, store_id: UUID, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.store_id == store_id, User.id == user_id)
        )
        return result.scalar_one_or_none()
