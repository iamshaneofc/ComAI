"""Add store_analytics_metrics table.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_analytics_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "key", name="uq_store_analytics_metric_store_key"),
    )
    op.create_index("ix_store_analytics_metrics_store_id", "store_analytics_metrics", ["store_id"], unique=False)
    op.create_index(
        "ix_store_analytics_metric_store_key",
        "store_analytics_metrics",
        ["store_id", "key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_store_analytics_metric_store_key", table_name="store_analytics_metrics")
    op.drop_index("ix_store_analytics_metrics_store_id", table_name="store_analytics_metrics")
    op.drop_table("store_analytics_metrics")
