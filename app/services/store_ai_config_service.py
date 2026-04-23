"""
Read/update per-tenant StoreAIConfig (provider, default model, encrypted API key).
"""
from uuid import UUID

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.field_crypto import encrypt_api_key
from app.models.store_ai_config import StoreAIConfig
from app.repositories.store_ai_config_repo import StoreAIConfigRepository
from app.schemas.ai_config import StoreAIConfigPatch, StoreAIConfigResponse

logger = structlog.get_logger(__name__)


class StoreAIConfigService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self._repo = StoreAIConfigRepository(db)

    def _defaults(self, store_id: UUID) -> StoreAIConfigResponse:
        prov = settings.ACTIVE_LLM_PROVIDER
        dm = settings.OPENAI_MODEL if prov == "openai" else settings.GEMINI_MODEL
        return StoreAIConfigResponse(
            id=None,
            store_id=store_id,
            provider=prov,
            default_model=dm,
            has_tenant_api_key=False,
        )

    async def get_config(self, store_id: UUID) -> StoreAIConfigResponse:
        row = await self._repo.get_by_store_id(store_id)
        if row is None:
            return self._defaults(store_id)
        return StoreAIConfigResponse(
            id=row.id,
            store_id=row.store_id,
            provider=row.provider,
            default_model=row.default_model,
            has_tenant_api_key=bool(row.api_key_encrypted),
        )

    async def patch_config(self, store_id: UUID, patch: StoreAIConfigPatch) -> StoreAIConfigResponse:
        row = await self._repo.get_by_store_id(store_id)
        if row is None:
            prov = patch.provider or settings.ACTIVE_LLM_PROVIDER
            dm = patch.default_model or (
                settings.OPENAI_MODEL if prov == "openai" else settings.GEMINI_MODEL
            )
            row = StoreAIConfig(
                store_id=store_id,
                provider=prov,
                default_model=dm,
                api_key_encrypted=None,
            )
            self.db.add(row)
            await self.db.flush()

        fs = patch.model_fields_set
        if "provider" in fs and patch.provider is not None:
            row.provider = patch.provider
        if "default_model" in fs and patch.default_model is not None:
            row.default_model = patch.default_model
        if "api_key" in fs:
            key = patch.api_key
            if key is None or (isinstance(key, str) and not key.strip()):
                row.api_key_encrypted = None
            else:
                row.api_key_encrypted = encrypt_api_key(key.strip())

        await self.db.flush()
        await self.db.refresh(row)
        logger.info("Store AI config updated", store_id=str(store_id), has_key=bool(row.api_key_encrypted))
        return StoreAIConfigResponse(
            id=row.id,
            store_id=row.store_id,
            provider=row.provider,
            default_model=row.default_model,
            has_tenant_api_key=bool(row.api_key_encrypted),
        )
