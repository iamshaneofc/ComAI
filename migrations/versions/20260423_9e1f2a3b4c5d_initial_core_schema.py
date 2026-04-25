"""Initial core schema for stores, products, users, events.

Revision ID: 9e1f2a3b4c5d
Revises:
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9e1f2a3b4c5d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False, server_default="custom"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("api_key", sa.String(length=64), nullable=False),
        sa.Column("credentials", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("whatsapp_phone_number", sa.String(length=20), nullable=True),
        sa.Column("ai_config", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stores_slug", "stores", ["slug"], unique=True)
    op.create_index("ix_stores_api_key", "stores", ["api_key"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_platform", sa.String(length=50), nullable=False, server_default="custom"),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("source", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("compare_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("inventory_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("images", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("variants", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=100)), nullable=True),
        sa.Column("categories", postgresql.ARRAY(sa.String(length=100)), nullable=True),
        sa.Column("searchable_text", sa.Text(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "external_id", name="uq_product_store_external_id"),
    )
    op.create_index("ix_products_store_id", "products", ["store_id"], unique=False)
    op.create_index("ix_products_searchable_text", "products", ["searchable_text"], unique=False)
    op.create_index("ix_products_store_available", "products", ["store_id", "is_available"], unique=False)
    op.create_index("ix_products_store_price", "products", ["store_id", "price"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("metadata_", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_store_id", "users", ["store_id"], unique=False)
    op.create_index("ix_users_external_id", "users", ["external_id"], unique=False)
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)
    op.create_index("ix_users_store_external_id", "users", ["store_id", "external_id"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_store_id", "events", ["store_id"], unique=False)
    op.create_index("ix_events_user_id", "events", ["user_id"], unique=False)
    op.create_index("ix_events_event_type", "events", ["event_type"], unique=False)
    op.create_index("ix_events_user_recent", "events", ["user_id", "created_at"], unique=False)
    op.create_index("ix_events_store_user", "events", ["store_id", "user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_events_store_user", table_name="events")
    op.drop_index("ix_events_user_recent", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_user_id", table_name="events")
    op.drop_index("ix_events_store_id", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_users_store_external_id", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_index("ix_users_store_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_products_store_price", table_name="products")
    op.drop_index("ix_products_store_available", table_name="products")
    op.drop_index("ix_products_searchable_text", table_name="products")
    op.drop_index("ix_products_store_id", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_stores_api_key", table_name="stores")
    op.drop_index("ix_stores_slug", table_name="stores")
    op.drop_table("stores")
