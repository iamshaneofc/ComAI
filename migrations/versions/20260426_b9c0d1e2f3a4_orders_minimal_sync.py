"""Add minimal orders table for order-status chat.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=True),
        sa.Column("customer_identifier", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("fulfillment_status", sa.String(length=64), nullable=False, server_default="unfulfilled"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "external_id", name="uq_orders_store_external"),
    )
    op.create_index("ix_orders_store_id", "orders", ["store_id"], unique=False)
    op.create_index("ix_orders_customer_identifier", "orders", ["customer_identifier"], unique=False)
    op.create_index("ix_orders_store_customer", "orders", ["store_id", "customer_identifier"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_store_customer", table_name="orders")
    op.drop_index("ix_orders_customer_identifier", table_name="orders")
    op.drop_index("ix_orders_store_id", table_name="orders")
    op.drop_table("orders")
