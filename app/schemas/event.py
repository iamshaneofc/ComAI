from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventIngestRequest(BaseModel):
    user_id: UUID
    event_type: str = Field(..., min_length=1, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)


class EventIngestResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_type: str
