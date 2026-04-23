"""Add Store.onboarding_status for onboarding progress polling.

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a8
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "b2c3d4e5f6a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "onboarding_status",
            sa.String(length=32),
            nullable=False,
            server_default="created",
        ),
    )
    op.create_check_constraint(
        "ck_stores_onboarding_status",
        "stores",
        "onboarding_status IN ('created', 'connected', 'syncing', 'ready', 'failed')",
    )
    # Stores that already have products are treated as fully onboarded.
    op.execute(
        """
        UPDATE stores s
        SET onboarding_status = 'ready'
        WHERE EXISTS (
            SELECT 1 FROM products p WHERE p.store_id = s.id
        )
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_stores_onboarding_status", "stores", type_="check")
    op.drop_column("stores", "onboarding_status")
