"""
Store AI configuration API — provider, default model, tenant API key (encrypted at rest).

Tenant is always ``request.state.store`` (X-API-KEY). Keys are never returned in responses.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.tenant import authenticated_store_id
from app.schemas.ai_config import StoreAIConfigPatch, StoreAIConfigResponse
from app.services.store_ai_config_service import StoreAIConfigService

router = APIRouter()


@router.get(
    "",
    response_model=StoreAIConfigResponse,
    summary="Get AI provider settings for this store",
)
async def get_ai_config(
    store_id: UUID = Depends(authenticated_store_id),
    service: StoreAIConfigService = Depends(StoreAIConfigService),
) -> StoreAIConfigResponse:
    return await service.get_config(store_id)


@router.patch(
    "",
    response_model=StoreAIConfigResponse,
    summary="Update AI provider settings (partial)",
)
async def patch_ai_config(
    payload: StoreAIConfigPatch,
    store_id: UUID = Depends(authenticated_store_id),
    service: StoreAIConfigService = Depends(StoreAIConfigService),
) -> StoreAIConfigResponse:
    return await service.patch_config(store_id, payload)
