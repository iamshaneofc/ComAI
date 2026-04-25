"""
Minimal tenant-scoped order mirror for order-status support.
"""
import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    order_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    fulfillment_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unfulfilled")
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("store_id", "external_id", name="uq_orders_store_external"),
        Index("ix_orders_store_customer", "store_id", "customer_identifier"),
    )
