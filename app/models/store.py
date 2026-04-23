"""
Store (Tenant) Model — root entity for multi-tenancy.

Every other model references store_id. This is the architectural boundary
between tenants. All queries MUST filter by store_id.
"""
from sqlalchemy import Boolean, CheckConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
import secrets


class Store(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "stores"
    __table_args__ = (
        CheckConstraint(
            "onboarding_status IN ('created', 'connected', 'syncing', 'ready', 'failed')",
            name="ck_stores_onboarding_status",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Source platform: shopify | custom | woocommerce
    platform: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(32))

    # Platform-specific connection config
    credentials: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    whatsapp_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # AI behavior config (JSON blob)
    ai_config: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provisioning / Shopify onboarding progress (for dashboard polling)
    onboarding_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="created",
        server_default="created",
    )

    @property
    def domain(self) -> str | None:
        """Shop/platform domain from unified `credentials` JSON (not a separate column)."""
        if not self.credentials:
            return None
        for key in ("shopify", "custom", "woocommerce"):
            block = self.credentials.get(key)
            if isinstance(block, dict):
                d = block.get("domain")
                if d:
                    return str(d)
        return None

    def __repr__(self) -> str:
        return f"<Store id={self.id} slug={self.slug} platform={self.platform}>"
