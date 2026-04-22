from uuid import UUID
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)

class UserService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
        self.repo = UserRepository(db)

    async def get_or_create_user(self, store_id: UUID, external_id: str) -> User:
        """Fetch existing user by session/phone/email, or create if missing."""
        user = await self.repo.get_by_external_id(store_id, external_id)
        if user:
            return user
        
        user = User(store_id=store_id, external_id=external_id)
        created = await self.repo.create(user)
        logger.info("Created new user", user_id=str(created.id), store_id=str(store_id))
        return created
