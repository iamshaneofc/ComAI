"""
Tenant-scoped Shopify metaobject mirror.
"""
import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class MetaObject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "metaobjects"

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("store_id", "key", name="uq_metaobjects_store_key"),
        Index("ix_metaobjects_store_key", "store_id", "key"),
    )
