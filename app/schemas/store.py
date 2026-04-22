"""
Store Pydantic Schemas — request/response models for the Store entity.

Rules:
    - No ORM imports
    - No business logic
    - Used by API layer for validation + serialization
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ----------------------------------------------------------------
# Request schemas (input)
# ----------------------------------------------------------------

class StoreCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, examples=["My Shopify Store"])
    platform: str = Field(..., examples=["shopify"])           # shopify | custom
    domain: str | None = Field(None, examples=["mystore.myshopify.com"])
    whatsapp_phone_number: str | None = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"shopify", "custom", "woocommerce"}
        if v.lower() not in allowed:
            raise ValueError(f"Platform must be one of: {allowed}")
        return v.lower()


class StoreUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    domain: str | None = None
    whatsapp_phone_number: str | None = None
    is_active: bool | None = None


# ----------------------------------------------------------------
# Response schemas (output)
# ----------------------------------------------------------------

class StoreResponse(BaseModel):
    model_config = {"from_attributes": True}   # enables ORM mode

    id: UUID
    name: str
    slug: str
    platform: str
    domain: str | None
    whatsapp_phone_number: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StoreCreatedResponse(StoreResponse):
    """Returned once after provisioning; includes the tenant API key."""

    api_key: str


class StoreSummary(BaseModel):
    """Lightweight response for list views."""
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    platform: str
    is_active: bool


class PaginatedStores(BaseModel):
    items: list[StoreSummary]
    total: int
    offset: int
    limit: int
