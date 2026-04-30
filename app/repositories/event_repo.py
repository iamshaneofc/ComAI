from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event import Event
from app.repositories.base import BaseRepository

class EventRepository(BaseRepository[Event]):
    def __init__(self, db: AsyncSession):
        super().__init__(model=Event, db=db)

    async def get_recent_events(self, store_id: UUID, user_id: UUID, limit: int = 20) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .where(Event.store_id == store_id, Event.user_id == user_id)
            .order_by(desc(Event.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_events_by_type(
        self,
        store_id: UUID,
        user_id: UUID,
        event_type: str,
        limit: int = 20,
    ) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .where(
                Event.store_id == store_id,
                Event.user_id == user_id,
                Event.event_type == event_type,
            )
            .order_by(desc(Event.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
