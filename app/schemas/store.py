"""
Store Pydantic Schemas — request/response models for the Store entity.

Rules:
    - No ORM imports
    - No business logic
    - Used by API layer for validation + serialization
"""
from datetime import datetime
from uuid import UUID

from typing import Literal

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

OnboardingStatusLiteral = Literal["created", "connected", "syncing", "ready", "failed"]


class StoreResponse(BaseModel):
    model_config = {"from_attributes": True}   # enables ORM mode

    id: UUID
    name: str
    slug: str
    platform: str
    domain: str | None
    whatsapp_phone_number: str | None
    is_active: bool
    onboarding_status: str
    created_at: datetime
    updated_at: datetime


class StoreMeStatusResponse(BaseModel):
    """Tenant onboarding progress for dashboard polling."""

    onboarding_status: OnboardingStatusLiteral
    products_count: int
    agent_ready: bool


class StoreCreatedResponse(StoreResponse):
    """Returned once after provisioning; includes the tenant API key."""

    api_key: str


ToneLiteral = Literal["friendly", "professional", "playful"]


class StoreOnboardRequest(BaseModel):
    """Connect a Shopify shop: credentials are stored; sync + default chat agent run in background."""

    platform: str = Field(..., examples=["shopify"])
    domain: str = Field(..., min_length=3, max_length=255, examples=["cool-brand.myshopify.com"])
    token: str = Field(..., min_length=8, max_length=512, description="Shopify Admin API access token")
    name: str | None = Field(
        None,
        min_length=2,
        max_length=255,
        description="Display name; derived from domain if omitted",
    )
    tone: ToneLiteral = Field(
        "friendly",
        description="Voice for the auto-generated chat agent system prompt",
    )
    industry_hint: str | None = Field(
        None,
        max_length=200,
        description="Optional vertical, e.g. fashion, electronics",
    )

    @field_validator("platform")
    @classmethod
    def platform_shopify_only(cls, v: str) -> str:
        p = v.lower().strip()
        if p != "shopify":
            raise ValueError("Onboarding currently supports platform=shopify only")
        return p

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        d = v.strip().lower()
        if ".." in d or d.startswith(".") or not d:
            raise ValueError("Invalid domain")
        return d


class StoreOnboardResponse(StoreCreatedResponse):
    """Store record plus acknowledgement that background onboarding was queued."""

    onboarding_job: str = Field(
        default="queued",
        description="Product sync + default chat agent setup scheduled via worker",
    )


class StoreSummary(BaseModel):
    """Lightweight response for list views."""
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    platform: str
    is_active: bool
    onboarding_status: str


class PaginatedStores(BaseModel):
    items: list[StoreSummary]
    total: int
    offset: int
    limit: int
