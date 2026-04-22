"""Store AI config and per-channel agents.

Revision ID: a1b2c3d4e5f7
Revises: f3a1b2c4d5e6
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "a1b2c3d4e5f7"
down_revision = "f3a1b2c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_ai_configs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="openai"),
        sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("default_model", sa.String(length=128), nullable=False, server_default="gpt-4o"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", name="uq_store_ai_configs_store_id"),
    )
    op.create_index(op.f("ix_store_ai_configs_store_id"), "store_ai_configs", ["store_id"], unique=False)

    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("store_id", UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.CheckConstraint("type IN ('chat', 'whatsapp', 'call')", name="ck_agents_type"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agents_store_id"), "agents", ["store_id"], unique=False)
    op.create_index("ix_agents_store_id_type", "agents", ["store_id", "type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agents_store_id_type", table_name="agents")
    op.drop_index(op.f("ix_agents_store_id"), table_name="agents")
    op.drop_table("agents")
    op.drop_index(op.f("ix_store_ai_configs_store_id"), table_name="store_ai_configs")
    op.drop_table("store_ai_configs")
