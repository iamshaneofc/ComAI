"""store_ai_configs: CHECK provider in (openai, gemini).

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-04-23
"""

from alembic import op

revision = "f7a8b9c0d1e2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_store_ai_configs_provider",
        "store_ai_configs",
        "provider IN ('openai', 'gemini')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_store_ai_configs_provider", "store_ai_configs", type_="check")
