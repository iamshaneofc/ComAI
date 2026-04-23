"""Agents: add name, enforce non-null model.

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("name", sa.String(length=128), nullable=False, server_default="Agent"),
    )
    op.execute("UPDATE agents SET model = 'gpt-4o' WHERE model IS NULL")
    op.alter_column(
        "agents",
        "model",
        existing_type=sa.String(length=128),
        nullable=False,
        server_default="gpt-4o",
    )


def downgrade() -> None:
    op.alter_column(
        "agents",
        "model",
        existing_type=sa.String(length=128),
        nullable=True,
        server_default=None,
    )
    op.drop_column("agents", "name")
