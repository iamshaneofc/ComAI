"""
Product Model — full-featured product schema with search support.

Architecture rules:
    - store_id is MANDATORY (multi-tenancy enforced at DB level)
    - searchable_text is the denormalized search document (title, description, tags, categories)
    - search_vector is a GENERATED tsvector (GIN-indexed) for @@ / to_tsquery search
    - tags/categories stored as ARRAY for filtering
    - images/variants/attributes stored as JSONB for flexibility
    - raw_data preserves original source payload (Shopify/custom) unchanged
"""
import uuid
from typing import Any

from sqlalchemy import Index, Numeric, String, Text, UniqueConstraint, Computed
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"

    # ----------------------------------------------------------------
    # Multi-tenancy — MUST be on every product query
    # ----------------------------------------------------------------
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # ----------------------------------------------------------------
    # Source tracking
    # ----------------------------------------------------------------
    source_platform: Mapped[str] = mapped_column(
        String(50), nullable=False, default="custom"
    )  # shopify | custom | woocommerce
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ----------------------------------------------------------------
    # Core product fields
    # ----------------------------------------------------------------
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    compare_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_available: Mapped[bool] = mapped_column(nullable=False, default=True)
    inventory_quantity: Mapped[int] = mapped_column(nullable=False, default=0)

    # ----------------------------------------------------------------
    # Structured JSON fields
    # ----------------------------------------------------------------
    images: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # e.g. [{"url": "...", "alt": "..."}]

    variants: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # e.g. [{"size": "M", "color": "Red", "price": 999, "sku": "X-M-R"}]

    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"material": "Cotton", "weight": "200g"}

    # ----------------------------------------------------------------
    # Categorical fields (ARRAY for efficient filtering)
    # ----------------------------------------------------------------
    tags: Mapped[list | None] = mapped_column(ARRAY(String(100)), nullable=True)
    categories: Mapped[list | None] = mapped_column(ARRAY(String(100)), nullable=True)

    # ----------------------------------------------------------------
    # Search optimisation (Database enforces generation on Upsert)
    # ----------------------------------------------------------------
    searchable_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, index=True
    )

    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR(),
        Computed(
            "to_tsvector('english', coalesce(searchable_text, "
            "lower(coalesce(title, '') || ' ' || coalesce(description, ''))))",
            persisted=True,
        ),
        nullable=False,
    )

    # ----------------------------------------------------------------
    # Preserve original payload (debugging + re-sync)
    # ----------------------------------------------------------------
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ----------------------------------------------------------------
    # Composite index for the most common query pattern
    # ----------------------------------------------------------------
    __table_args__ = (
        Index("ix_products_store_available", "store_id", "is_available"),
        Index("ix_products_store_price", "store_id", "price"),
        Index("ix_products_search_vector", "search_vector", postgresql_using="gin"),
        UniqueConstraint("store_id", "external_id", name="uq_product_store_external_id"),
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} title={self.title[:40]!r}>"
