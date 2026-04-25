"""
Store Pydantic Schemas — request/response models for the Store entity.

Rules:
    - No ORM imports
    - No business logic
    - Used by API layer for validation + serialization
"""
from datetime import datetime
from uuid import UUID

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


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
    """Connect a store for automatic product sync (Shopify or custom JSON feed)."""

    platform: str = Field(..., examples=["shopify", "custom"])
    domain: str = Field(..., min_length=3, max_length=255, examples=["cool-brand.myshopify.com", "brand.com"])
    token: str = Field(
        default="",
        max_length=512,
        description="Optional legacy: Admin API token (shpat_/shpca_). Not used for catalog sync.",
    )
    client_id: str = Field(
        default="",
        max_length=255,
        description="Optional: kept in credentials for future use; not used for catalog sync.",
    )
    client_secret: str = Field(
        default="",
        max_length=512,
        description="Optional: kept in credentials for future use; not used for catalog sync.",
    )
    webhook_secret: str = Field(
        default="",
        max_length=512,
        description="Optional: required only if you use Shopify webhooks (HMAC verification).",
    )
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
    custom_products_url: str = Field(
        default="",
        max_length=2000,
        description="Required for platform=custom. Public JSON endpoint returning products.",
    )
    custom_items_path: str = Field(
        default="",
        max_length=255,
        description="Optional dot path to array in JSON (e.g. data.products). Empty means root list.",
    )
    custom_field_map: dict[str, str] | None = Field(
        default=None,
        description=(
            "Optional map from ProductCreate fields to JSON paths in each item. "
            "Example: {'title':'name','price':'pricing.amount','images':'media.images'}"
        ),
    )

    @field_validator("platform")
    @classmethod
    def platform_supported(cls, v: str) -> str:
        p = v.lower().strip()
        if p not in {"shopify", "custom"}:
            raise ValueError("Onboarding currently supports platform=shopify or platform=custom")
        return p

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        d = v.strip().lower()
        if ".." in d or d.startswith(".") or not d:
            raise ValueError("Invalid domain")
        return d

    @model_validator(mode="before")
    @classmethod
    def default_webhook_secret_for_oauth_only(cls, data: Any) -> Any:
        """OAuth-only onboard: copy client_secret into webhook_secret when webhook is omitted."""
        if not isinstance(data, dict):
            return data
        token = str(data.get("token") or "").strip()
        cid = str(data.get("client_id") or "").strip()
        csec = str(data.get("client_secret") or "").strip()
        wh = str(data.get("webhook_secret") or "").strip()
        has_admin = bool(token)
        has_oauth = bool(cid and csec)
        if has_oauth and not wh and not has_admin:
            return {**data, "webhook_secret": csec}
        return data

    @model_validator(mode="after")
    def shopify_auth_optional(self) -> Self:
        """
        Validate platform-specific onboarding rules.

        - custom: requires JSON feed URL
        - shopify: domain-only is valid; optional Admin/OAuth fields validated when provided
        """
        if self.platform == "custom":
            if not self.custom_products_url.strip():
                raise ValueError("custom_products_url is required when platform=custom")
            return self

        t = self.token.strip()
        cid = self.client_id.strip()
        csec = self.client_secret.strip()
        wh = self.webhook_secret.strip()
        has_admin = bool(t)
        has_oauth = bool(cid and csec)
        catalog_only = not has_admin and not has_oauth

        if catalog_only:
            return self

        if has_admin and t.startswith("shpss_"):
            raise ValueError(
                "token looks like the app client secret (shpss_), not an Admin API access token. "
                "Leave token empty for domain-only onboarding."
            )
        if has_admin and not wh:
            raise ValueError("webhook_secret is required when storing an Admin API token (shpat_/shpca_).")
        if len(wh) < 8:
            raise ValueError(
                "webhook_secret must be at least 8 characters when using Admin token or OAuth credentials."
            )
        return self


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


class PlatformStoreListItem(BaseModel):
    """
    Dev-console row: includes full tenant api_key.

    Only returned from GET /api/v1/platform/stores with X-Provision-Secret.
    Never expose this endpoint on the public internet.
    """

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    platform: str
    domain: str | None
    onboarding_status: str
    is_active: bool
    created_at: datetime
    api_key: str


class PaginatedPlatformStores(BaseModel):
    items: list[PlatformStoreListItem]
    total: int
    offset: int
    limit: int
