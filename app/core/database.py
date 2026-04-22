"""
Database — Async SQLAlchemy engine, session factory, and FastAPI dependency.

Rules:
    - Only this file creates engine/session objects
    - Use `async with get_db() as db` in repositories ONLY
    - Never import session directly in services or API layer
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ----------------------------------------------------------------
# Engine — created once, shared across the application
# ----------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,      # SQL logging in dev only
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,           # Validates connection before use
    pool_recycle=3600,            # Recycle connections every hour
)

# ----------------------------------------------------------------
# Session factory
# ----------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # Prevent lazy loading after commit
    autocommit=False,
    autoflush=False,
)


# ----------------------------------------------------------------
# FastAPI dependency — inject into repositories via Depends()
# ----------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields an async database session, commits on success, rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
