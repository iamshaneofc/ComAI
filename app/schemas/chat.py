"""
Chat Pydantic Schemas — Phase 1 (simplified for MVP).

Changes from previous version:
    - ChatRequest accepts store_id directly in the body (no auth header needed for Phase 1)
    - ChatResponse includes products list and intent
    - Removed session_id, channel, quick_replies (Phase 2)
"""
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = Field(None, description="External User ID matching their session or phone")
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")


class ProductCard(BaseModel):
    """Lightweight product representation in chat response."""
    id: str
    title: str
    price: float
    currency: str
    images: list[dict] | None = None
    tags: list[str] | None = None
    is_available: bool = True


class ChatResponse(BaseModel):
    message: str
    intent: str
    products: list[dict] = []           # list of ProductSummary dicts
