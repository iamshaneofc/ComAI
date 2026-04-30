from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=ChatMessage, db=db)

    async def add_message(
        self,
        *,
        store_id: UUID,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> ChatMessage:
        row = ChatMessage(
            store_id=store_id,
            session_id=session_id.strip(),
            role=role.strip().lower(),
            content=content,
            metadata=metadata or {},
        )
        return await self.create(row)

    async def get_recent_messages(
        self,
        *,
        store_id: UUID,
        session_id: str,
        limit: int = 10,
    ) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.store_id == store_id,
                ChatMessage.session_id == session_id.strip(),
            )
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
