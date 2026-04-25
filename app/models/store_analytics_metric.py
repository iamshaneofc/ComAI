"""
Tenant-scoped aggregated analytics metrics for owner dashboards.
"""
import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class StoreAnalyticsMetric(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "store_analytics_metrics"

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("store_id", "key", name="uq_store_analytics_metric_store_key"),
        Index("ix_store_analytics_metric_store_key", "store_id", "key"),
    )
