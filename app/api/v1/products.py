"""
Products API — CRUD + search endpoints.

Endpoints:
    POST   /products              → Create a product
    POST   /products/bulk         → Bulk create (for seeding / sync)
    GET    /products/search       → Full search with filters
    GET    /products/{product_id} → Get by ID

All endpoints require X-Store-ID header for multi-tenancy.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.modules.products.service import ProductService
from app.schemas.product import (
    PaginatedProducts,
    ProductCreate,
    ProductResponse,
    ProductSearchFilters,
)

router = APIRouter()


def get_store_id(x_store_id: UUID = Header(..., description="Tenant Store ID")) -> UUID:
    """Extract and validate store_id from X-Store-ID header."""
    return x_store_id


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a single product",
)
async def create_product(
    payload: ProductCreate,
    store_id: UUID = Depends(get_store_id),
    service: ProductService = Depends(ProductService),
) -> ProductResponse:
    """Create one product in the store's catalogue."""
    return await service.create_product(store_id, payload)


@router.post(
    "/bulk",
    response_model=list[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create products (seed / sync)",
)
async def bulk_create_products(
    payload: list[ProductCreate],
    store_id: UUID = Depends(get_store_id),
    service: ProductService = Depends(ProductService),
) -> list[ProductResponse]:
    """
    Insert up to 100 products in a single transaction.
    Use this to seed your store catalogue for testing.
    """
    if len(payload) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 products per bulk insert",
        )
    return await service.bulk_create_products(store_id, payload)


@router.get(
    "/search",
    response_model=PaginatedProducts,
    summary="Search products with filters",
)
async def search_products(
    keyword: str | None = Query(None, description="Search keyword"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, gt=0),
    category: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    store_id: UUID = Depends(get_store_id),
    service: ProductService = Depends(ProductService),
) -> PaginatedProducts:
    """
    Search store products with optional filters.

    Supports:
    - `keyword`: ILIKE search on title, description, and tags
    - `min_price` / `max_price`: price range filter
    - `category`: exact category match
    """
    filters = ProductSearchFilters(
        keyword=keyword,
        min_price=min_price,
        max_price=max_price,
        category=category,
        offset=offset,
        limit=limit,
    )
    return await service.search_products(store_id, filters)
