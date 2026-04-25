"""
Platform (dev-console) routes — gated by X-Provision-Secret only.

GET /platform/stores returns every tenant row including full api_key so the
internal admin UI can impersonate a store. DELETE /platform/stores/{id} soft-deactivates
a tenant (same as tenant DELETE /stores/me). Dev / local use only; do not expose
publicly on the internet.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import verify_provision_secret
from app.modules.stores.service import StoreService
from app.schemas.store import PaginatedPlatformStores, PlatformStoreListItem

router = APIRouter(dependencies=[Depends(verify_provision_secret)])


@router.get(
    "/stores",
    response_model=PaginatedPlatformStores,
    summary="List all stores (platform / dev console)",
    description=(
        "Requires X-Provision-Secret matching APP_SECRET_KEY. "
        "Returns full tenant api_key per row for local dev-console impersonation — "
        "never expose this route on a public host."
    ),
)
async def list_all_stores(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True, description="If true, only is_active stores"),
    service: StoreService = Depends(StoreService),
) -> PaginatedPlatformStores:
    stores, total = await service.list_stores(offset=offset, limit=limit, active_only=active_only)
    items = [PlatformStoreListItem.model_validate(s) for s in stores]
    return PaginatedPlatformStores(items=items, total=total, offset=offset, limit=limit)


@router.delete(
    "/stores/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a store (platform / dev console)",
    description=(
        "Requires X-Provision-Secret matching APP_SECRET_KEY. "
        "Sets is_active=false for the store (soft delete); API key no longer authenticates."
    ),
)
async def deactivate_store_platform(
    store_id: UUID,
    service: StoreService = Depends(StoreService),
) -> None:
    await service.deactivate_store(store_id)
