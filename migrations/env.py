"""
Alembic Async Migration Environment

Reads DATABASE_URL from .env (via Settings) so migrations always
use the correct database — never hardcoded credentials.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import ALL models so Alembic can detect schema changes
from app.core.config import settings
from app.models.base import Base
from app.models.store import Store  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.store_ai_config import StoreAIConfig  # noqa: F401
from app.models.agent import Agent  # noqa: F401

# Alembic config object (reads alembic.ini)
config = context.config

# Override sqlalchemy.url from settings (do NOT hardcode in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for --autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
