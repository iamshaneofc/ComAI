from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.repositories.order_repo import OrderRepository


class OrderService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.repo = OrderRepository(db)

    @staticmethod
    def _user_identifiers(user: User) -> list[str]:
        ids: list[str] = []
        ext = str(user.external_id or "").strip().lower()
        if "@" in ext:
            ids.append(f"email:{ext}")
        else:
            ext_phone = "".join(ch for ch in ext if ch.isdigit() or ch == "+")
            if ext_phone:
                ids.append(f"phone:{ext_phone}")
        if user.phone and str(user.phone).strip():
            phone = "".join(ch for ch in str(user.phone).strip().lower() if ch.isdigit() or ch == "+")
            if phone:
                ids.append(f"phone:{phone}")
        meta = user.metadata_ if isinstance(user.metadata_, dict) else {}
        email = str(meta.get("email") or "").strip().lower()
        if email:
            ids.append(f"email:{email}")
        return ids

    async def find_latest_order_for_user(self, store_id: UUID, user: User) -> dict | None:
        for identifier in self._user_identifiers(user):
            rows = await self.repo.find_recent_for_customer(store_id, identifier, limit=1)
            if rows:
                row = rows[0]
                return {
                    "order_number": row.order_number or row.external_id,
                    "status": row.status,
                    "fulfillment_status": row.fulfillment_status,
                }
        return None
