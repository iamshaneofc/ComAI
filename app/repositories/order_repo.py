from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Order, db=db)

    async def upsert_bulk(self, rows: list[Order]) -> None:
        if not rows:
            return
        values = [
            {
                "id": r.id,
                "store_id": r.store_id,
                "external_id": r.external_id,
                "order_number": r.order_number,
                "customer_identifier": r.customer_identifier,
                "status": r.status,
                "fulfillment_status": r.fulfillment_status,
                "metadata": r.metadata,
            }
            for r in rows
        ]
        stmt = insert(Order).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["store_id", "external_id"],
            set_={
                "order_number": stmt.excluded.order_number,
                "customer_identifier": stmt.excluded.customer_identifier,
                "status": stmt.excluded.status,
                "fulfillment_status": stmt.excluded.fulfillment_status,
                "metadata": stmt.excluded.metadata,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self.db.execute(stmt)

    async def find_recent_for_customer(
        self,
        store_id: UUID,
        customer_identifier: str,
        *,
        limit: int = 3,
    ) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(
                Order.store_id == store_id,
                Order.customer_identifier == customer_identifier.strip().lower(),
            )
            .order_by(Order.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
