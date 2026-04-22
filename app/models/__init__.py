"""
Models package — import all ORM models here.

This ensures Alembic can discover all tables for --autogenerate
and SQLAlchemy metadata is fully populated before migrations run.
"""
from app.models.base import Base  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.store import Store  # noqa: F401
from app.models.store_ai_config import StoreAIConfig  # noqa: F401
from app.models.agent import Agent  # noqa: F401

__all__ = ["Base", "Store", "Product", "StoreAIConfig", "Agent"]
