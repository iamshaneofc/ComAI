from collections import Counter
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.event import Event
from app.repositories.event_repo import EventRepository
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)


class MemoryService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.repo = EventRepository(db)
        self.users = UserRepository(db)

    async def track_event(self, store_id: UUID, user_id: UUID, event_type: str, payload: dict) -> Event:
        """Stores a behavioral event; user must belong to the same tenant."""
        user = await self.users.get_by_id_for_store(store_id, user_id)
        if user is None:
            raise HTTPException(
                status_code=403,
                detail="Cannot record event: user does not belong to this store",
            )
        event = Event(store_id=store_id, user_id=user_id, event_type=event_type, payload=payload)
        created = await self.repo.create(event)
        logger.debug("Event tracked", event_type=event_type, user_id=str(user_id))
        return created

    async def get_user_preferences(self, store_id: UUID, user_id: UUID) -> dict:
        """Fetch last 20 events for a user scoped to this store only."""
        user = await self.users.get_by_id_for_store(store_id, user_id)
        if user is None:
            return {
                "top_categories": [],
                "avg_price_limit": None,
                "recent_searches": [],
            }

        events = await self.repo.get_recent_events(store_id, user_id, limit=20)

        categories = []
        prices = []
        recent_searches = []

        for event in events:
            if event.store_id != store_id:
                logger.error("Event row store_id mismatch", event_id=str(event.id))
                continue
            if event.event_type == "search":
                if event.payload.get("categories"):
                    categories.extend(event.payload["categories"])
                if event.payload.get("price_limit"):
                    prices.append(float(event.payload["price_limit"]))
                if event.payload.get("keywords"):
                    recent_searches.extend(event.payload["keywords"])

        top_categories = [cat for cat, _ in Counter(categories).most_common(3)]
        avg_price = sum(prices) / len(prices) if prices else None

        return {
            "top_categories": top_categories,
            "avg_price_limit": avg_price,
            "recent_searches": recent_searches[:5],
        }
