"""Add store_contents and metaobjects tables.

Revision ID: a8b9c0d1e2f3
Revises: c9d8e7f6a5b4
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a8b9c0d1e2f3"
down_revision = "c9d8e7f6a5b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_contents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False, server_default="page"),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "external_id", name="uq_store_content_store_external"),
    )
    op.create_index("ix_store_contents_store_id", "store_contents", ["store_id"], unique=False)
    op.create_index("ix_store_content_store_type", "store_contents", ["store_id", "type"], unique=False)

    op.create_table(
        "metaobjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "key", name="uq_metaobjects_store_key"),
    )
    op.create_index("ix_metaobjects_store_id", "metaobjects", ["store_id"], unique=False)
    op.create_index("ix_metaobjects_store_key", "metaobjects", ["store_id", "key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_metaobjects_store_key", table_name="metaobjects")
    op.drop_index("ix_metaobjects_store_id", table_name="metaobjects")
    op.drop_table("metaobjects")

    op.drop_index("ix_store_content_store_type", table_name="store_contents")
    op.drop_index("ix_store_contents_store_id", table_name="store_contents")
    op.drop_table("store_contents")
