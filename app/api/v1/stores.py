"""
Stores API — provisioning (master secret) + tenant-scoped management (API key).

Tenant mutations use only `/stores/me` — no store UUID in path or query (cannot be spoofed).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status

from app.api.dependencies import verify_provision_secret
from app.modules.stores.service import StoreService
from app.schemas.store import (
    PaginatedStores,
    StoreCreate,
    StoreCreatedResponse,
    StoreResponse,
    StoreSummary,
    StoreUpdate,
)

provision_router = APIRouter()
tenant_router = APIRouter()


@provision_router.post(
    "",
    response_model=StoreCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new store (platform secret)",
    dependencies=[Depends(verify_provision_secret)],
)
async def create_store(
    payload: StoreCreate,
    service: StoreService = Depends(StoreService),
) -> StoreCreatedResponse:
    """Creates a new tenant store. Requires X-Provision-Secret matching APP_SECRET_KEY."""
    store = await service.create_store(payload)
    return StoreCreatedResponse.model_validate(store)


@tenant_router.get(
    "/me",
    response_model=StoreResponse,
    summary="Get the authenticated store",
)
async def get_current_store(request: Request) -> StoreResponse:
    return StoreResponse.model_validate(request.state.store)


@tenant_router.patch(
    "/me",
    response_model=StoreResponse,
    summary="Update the authenticated store",
)
async def update_current_store(
    request: Request,
    payload: StoreUpdate,
    service: StoreService = Depends(StoreService),
) -> StoreResponse:
    store_id = request.state.store.id
    store = await service.update_store(store_id, payload)
    return StoreResponse.model_validate(store)


@tenant_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate the authenticated store (soft delete)",
)
async def deactivate_current_store(request: Request, service: StoreService = Depends(StoreService)) -> None:
    await service.deactivate_store(request.state.store.id)


@tenant_router.post(
    "/me/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger product sync for the authenticated store",
)
async def sync_current_store_products(
    request: Request,
    background_tasks: BackgroundTasks,
    service: StoreService = Depends(StoreService),
):
    sid = request.state.store.id
    background_tasks.add_task(service.sync_store_products, sid)
    return {"status": "sync_started", "store_id": sid}


@tenant_router.get(
    "",
    response_model=PaginatedStores,
    summary="List stores (authenticated tenant only)",
)
async def list_stores(
    request: Request,
    offset: int = Query(0, ge=0, description="Pagination offset (reserved)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page (reserved)"),
) -> PaginatedStores:
    """Returns only the caller's store — no global tenant listing."""
    store = request.state.store
    return PaginatedStores(
        items=[StoreSummary.model_validate(store)],
        total=1,
        offset=offset,
        limit=limit,
    )
