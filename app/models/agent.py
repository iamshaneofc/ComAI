"""
Channel-scoped AI agent configuration per store (chat, whatsapp, call).
"""
import uuid

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Agent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint(
            "type IN ('chat', 'whatsapp', 'call')",
            name="ck_agents_type",
        ),
        Index("ix_agents_store_id_type", "store_id", "type"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)

    model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
