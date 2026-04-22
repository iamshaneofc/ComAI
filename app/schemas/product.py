"""
Product Pydantic Schemas — request/response models.

Rules:
    - No ORM imports, no business logic
    - ProductCreate is what the API / sync service receives
    - ProductResponse is what the API sends back (ORM mode on)
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ----------------------------------------------------------------
# Request schemas
# ----------------------------------------------------------------

class ProductCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    price: float = Field(..., gt=0)
    compare_price: float | None = None
    currency: str = Field("INR", max_length=10)
    sku: str | None = None
    is_available: bool = True
    inventory_quantity: int = Field(0, ge=0)

    images: list[dict] | None = None      # [{"url": "...", "alt": "..."}]
    variants: list[dict] | None = None    # [{"size": "M", "price": 999}]
    attributes: dict | None = None        # {"material": "Cotton"}

    tags: list[str] | None = None
    categories: list[str] | None = None

    source_platform: str = "custom"
    external_id: str | None = None
    source: dict | None = None
    raw_data: dict | None = None


class ProductSearchFilters(BaseModel):
    keyword: str | None = None
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, gt=0)
    category: str | None = None
    tags: list[str] | None = None
    is_available: bool = True
    limit: int = Field(10, ge=1, le=50)
    offset: int = Field(0, ge=0)


# ----------------------------------------------------------------
# Response schemas
# ----------------------------------------------------------------

class ProductResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    store_id: UUID
    title: str
    description: str | None
    price: float
    compare_price: float | None
    currency: str
    sku: str | None
    is_available: bool
    inventory_quantity: int
    images: list[dict] | None
    variants: list[dict] | None
    attributes: dict | None
    tags: list[str] | None
    categories: list[str] | None
    source_platform: str
    external_id: str | None
    source: dict | None
    created_at: datetime
    updated_at: datetime


class ProductSummary(BaseModel):
    """Lightweight card used in chat responses."""
    model_config = {"from_attributes": True}

    id: UUID
    title: str
    price: float
    currency: str
    images: list[dict] | None
    tags: list[str] | None
    is_available: bool


class PaginatedProducts(BaseModel):
    items: list[ProductResponse]
    total: int
    offset: int
    limit: int
