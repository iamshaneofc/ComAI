import uuid
from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    store_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("ix_users_store_id", "store_id"),
        Index("ix_users_external_id", "external_id"),
        Index("ix_users_store_external_id", "store_id", "external_id", unique=True),
    )
