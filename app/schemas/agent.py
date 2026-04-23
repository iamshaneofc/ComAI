"""
Pydantic schemas for tenant-scoped Agent CRUD (API body/response).
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AgentTypeLiteral = Literal["chat", "whatsapp", "call"]
ChatToneLiteral = Literal["friendly", "premium", "aggressive"]
ChatGoalLiteral = Literal["sales", "support", "upsell"]


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: AgentTypeLiteral
    model: str | None = Field(
        None,
        max_length=128,
        description="LLM model id; omit or empty to use store AI default_model or platform default",
    )
    system_prompt: str = Field(..., min_length=1, max_length=50_000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    is_active: bool = True
    tone: ChatToneLiteral = "friendly"
    goal: ChatGoalLiteral = "sales"
    language: str | None = Field(None, max_length=32)


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    type: AgentTypeLiteral | None = None
    model: str | None = Field(None, max_length=128)
    system_prompt: str | None = Field(None, min_length=1, max_length=50_000)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    is_active: bool | None = None
    tone: ChatToneLiteral | None = None
    goal: ChatGoalLiteral | None = None
    language: str | None = Field(None, max_length=32)


class AgentResponse(BaseModel):
    id: UUID
    name: str
    type: str
    model: str
    system_prompt: str
    temperature: float
    is_active: bool
    tone: str
    goal: str
    language: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentChatPatch(BaseModel):
    """Partial update for the store's active chat agent; ``system_prompt`` is always regenerated server-side."""

    name: str | None = Field(None, min_length=1, max_length=128)
    tone: ChatToneLiteral | None = None
    goal: ChatGoalLiteral | None = None
    language: str | None = Field(
        None,
        max_length=32,
        description="BCP-47 or short label, e.g. en, hi. Send empty string to clear.",
    )
    model: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0.0, le=2.0)


class AgentChatConfigResponse(BaseModel):
    """Active chat agent behaviour + generated system prompt (read model)."""

    id: UUID
    name: str
    type: str
    model: str
    temperature: float
    tone: str
    goal: str
    language: str | None
    system_prompt: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
