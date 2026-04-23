"""Agents: tone, goal, optional language for editable chat behaviour.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("tone", sa.String(length=32), nullable=False, server_default="friendly"),
    )
    op.add_column(
        "agents",
        sa.Column("goal", sa.String(length=32), nullable=False, server_default="sales"),
    )
    op.add_column(
        "agents",
        sa.Column("language", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "ck_agents_tone",
        "agents",
        "tone IN ('friendly', 'premium', 'aggressive')",
    )
    op.create_check_constraint(
        "ck_agents_goal",
        "agents",
        "goal IN ('sales', 'support', 'upsell')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_agents_goal", "agents", type_="check")
    op.drop_constraint("ck_agents_tone", "agents", type_="check")
    op.drop_column("agents", "language")
    op.drop_column("agents", "goal")
    op.drop_column("agents", "tone")
