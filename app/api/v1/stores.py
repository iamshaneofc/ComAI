"""
Stores API Endpoints — POST, GET, PATCH, DELETE for store (tenant) management.

Rules:
    - NO business logic here
    - Validate input (Pydantic), call service, return response
    - Use Depends() for service injection
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, BackgroundTasks

from app.modules.stores.service import StoreService
from app.modules.stores.service import StoreService
from app.schemas.store import (
    PaginatedStores,
    StoreCreate,
    StoreResponse,
    StoreSummary,
    StoreUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new store (tenant)",
)
async def create_store(
    payload: StoreCreate,
    service: StoreService = Depends(StoreService),
) -> StoreResponse:
    """
    Creates a new tenant store.

    - Auto-generates a unique slug from the name
    - Platform must be: shopify | custom | woocommerce
    """
    store = await service.create_store(payload)
    return StoreResponse.model_validate(store)


@router.get(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Get store by ID",
)
async def get_store(
    store_id: UUID,
    service: StoreService = Depends(StoreService),
) -> StoreResponse:
    """Fetch a store by its UUID. Returns 404 if not found."""
    store = await service.get_store(store_id)
    return StoreResponse.model_validate(store)


@router.get(
    "",
    response_model=PaginatedStores,
    summary="List all stores",
)
async def list_stores(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    active_only: bool = Query(True, description="Filter to active stores only"),
    service: StoreService = Depends(StoreService),
) -> PaginatedStores:
    """Returns a paginated list of stores."""
    stores, total = await service.list_stores(
        offset=offset, limit=limit, active_only=active_only
    )
    return PaginatedStores(
        items=[StoreSummary.model_validate(s) for s in stores],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.patch(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Partially update a store",
)
async def update_store(
    store_id: UUID,
    payload: StoreUpdate,
    service: StoreService = Depends(StoreService),
) -> StoreResponse:
    """Partial update — only fields provided in the body are changed."""
    store = await service.update_store(store_id, payload)
    return StoreResponse.model_validate(store)


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a store (soft delete)",
)
async def deactivate_store(
    store_id: UUID,
    service: StoreService = Depends(StoreService),
) -> None:
    """Soft-deletes a store by setting is_active=False."""
    await service.deactivate_store(store_id)


@router.post(
    "/{store_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger products sync for a store",
)
async def sync_store_products(
    store_id: UUID,
    background_tasks: BackgroundTasks,
    service: StoreService = Depends(StoreService),
):
    """
    Triggers an asynchronous synchronization pipeline downloading
    and upsetting shopify products incrementally. 
    """
    background_tasks.add_task(service.sync_store_products, store_id)
    return {"status": "sync_started", "store_id": store_id}
