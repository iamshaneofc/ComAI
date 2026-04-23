"""
Per-tenant AI provider settings (API key at rest, default model).

Secrets live in api_key_encrypted; use app.core.field_crypto to encrypt/decrypt.
"""
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class StoreAIConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "store_ai_configs"
    __table_args__ = (
        UniqueConstraint("store_id", name="uq_store_ai_configs_store_id"),
        CheckConstraint("provider IN ('openai', 'gemini')", name="ck_store_ai_configs_provider"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # openai | gemini — align with settings.ACTIVE_LLM_PROVIDER
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")

    api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    default_model: Mapped[str] = mapped_column(String(128), nullable=False, default="gpt-4o")
