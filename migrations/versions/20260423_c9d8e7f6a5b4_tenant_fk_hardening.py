"""Harden tenant store foreign keys on core tables.

Revision ID: c9d8e7f6a5b4
Revises: f7a8b9c0d1e2
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa

revision = "c9d8e7f6a5b4"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("products", "store_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("users", "store_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("events", "store_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_products_store_id_stores') THEN
                ALTER TABLE products
                ADD CONSTRAINT fk_products_store_id_stores
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_store_id_stores') THEN
                ALTER TABLE users
                ADD CONSTRAINT fk_users_store_id_stores
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_events_store_id_stores') THEN
                ALTER TABLE events
                ADD CONSTRAINT fk_events_store_id_stores
                FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE;
            END IF;
        END
        $$;
        """
    )

def downgrade() -> None:
    op.drop_constraint("fk_events_store_id_stores", "events", type_="foreignkey")
    op.drop_constraint("fk_users_store_id_stores", "users", type_="foreignkey")
    op.drop_constraint("fk_products_store_id_stores", "products", type_="foreignkey")
