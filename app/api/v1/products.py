"""
Products API — CRUD + search. Tenant is always `request.state.store` (API key).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.tenant import authenticated_store_id
from app.modules.products.service import ProductService
from app.schemas.product import (
    PaginatedProducts,
    ProductCreate,
    ProductResponse,
    ProductSearchFilters,
)

router = APIRouter()


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a single product",
)
async def create_product(
    payload: ProductCreate,
    store_id: UUID = Depends(authenticated_store_id),
    service: ProductService = Depends(ProductService),
) -> ProductResponse:
    return await service.create_product(store_id, payload)


@router.post(
    "/bulk",
    response_model=list[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create products (seed / sync)",
)
async def bulk_create_products(
    payload: list[ProductCreate],
    store_id: UUID = Depends(authenticated_store_id),
    service: ProductService = Depends(ProductService),
) -> list[ProductResponse]:
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
    store_id: UUID = Depends(authenticated_store_id),
    service: ProductService = Depends(ProductService),
) -> PaginatedProducts:
    filters = ProductSearchFilters(
        keyword=keyword,
        min_price=min_price,
        max_price=max_price,
        category=category,
        offset=offset,
        limit=limit,
    )
    return await service.search_products(store_id, filters)
