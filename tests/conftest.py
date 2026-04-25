"""
Pytest configuration — PostgreSQL integration fixtures.
"""
from collections.abc import AsyncGenerator
from os import getenv
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.store import Store

TEST_DATABASE_URL = getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/comai_test")
if "postgresql" not in TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must point to PostgreSQL")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_db() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_store(db_session: AsyncSession):
    async def _make_store(*, name: str, slug: str, api_key: str, platform: str = "shopify", credentials: dict | None = None):
        row = Store(
            name=name,
            slug=slug,
            platform=platform,
            api_key=api_key,
            credentials=credentials,
            onboarding_status="created",
            is_active=True,
        )
        db_session.add(row)
        await db_session.flush()
        await db_session.refresh(row)
        return row

    return _make_store


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.generate.return_value = AsyncMock(
        text="I can help you find the perfect product!",
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
    )
    return mock
