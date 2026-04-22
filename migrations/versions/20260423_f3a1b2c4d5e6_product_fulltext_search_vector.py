"""Product full-text search: tsvector from searchable_text + GIN index.

Replaces title-only generated column (if present) with a vector aligned to
the same text used for legacy ILIKE search (searchable_text, with fallback
to title + description).

Revision ID: f3a1b2c4d5e6
Revises:
Create Date: 2026-04-23
"""

from alembic import op

revision = "f3a1b2c4d5e6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS search_vector")
    op.execute(
        """
        ALTER TABLE products ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                coalesce(
                    searchable_text,
                    lower(coalesce(title, '') || ' ' || coalesce(description, ''))
                )
            )
        ) STORED
        """
    )
    op.create_index(
        "ix_products_search_vector",
        "products",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_products_search_vector", table_name="products")
    op.drop_column("products", "search_vector")
