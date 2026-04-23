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
        CheckConstraint(
            "tone IN ('friendly', 'premium', 'aggressive')",
            name="ck_agents_tone",
        ),
        CheckConstraint(
            "goal IN ('sales', 'support', 'upsell')",
            name="ck_agents_goal",
        ),
        Index("ix_agents_store_id_type", "store_id", "type"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Agent")

    type: Mapped[str] = mapped_column(String(32), nullable=False)

    model: Mapped[str] = mapped_column(String(128), nullable=False, default="gpt-4o")

    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # User-facing behaviour (chat); system_prompt is derived/regenerated from these + catalogue context
    tone: Mapped[str] = mapped_column(String(32), nullable=False, default="friendly")
    goal: Mapped[str] = mapped_column(String(32), nullable=False, default="sales")
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
