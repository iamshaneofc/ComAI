"""
Resolve per-store, per-channel LLM runtime config (Agent + StoreAIConfig) with defaults.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt.builder import SYSTEM_PROMPT
from app.core.config import settings
from app.core.field_crypto import decrypt_api_key
from app.models.store_ai_config import StoreAIConfig
from app.repositories.agent_repo import AgentRepository
from app.repositories.store_ai_config_repo import StoreAIConfigRepository

logger = structlog.get_logger(__name__)

AgentType = Literal["chat", "whatsapp", "call"]


@dataclass(frozen=True, slots=True)
class ResolvedAgentConfig:
    """Runtime LLM settings after resolution (secrets never logged)."""

    provider: str
    model: str
    temperature: float
    system_prompt: str
    api_key: str | None
    fallback_used: bool
    agent_id: UUID | None


class AgentService:
    """Orchestrates AgentRepository + store AI settings for chat and other channels."""

    def __init__(self, db: AsyncSession) -> None:
        self._agents = AgentRepository(db)
        self._store_ai = StoreAIConfigRepository(db)

    async def resolve_agent(self, store_id: UUID, agent_type: AgentType) -> ResolvedAgentConfig:
        store_cfg = await self._store_ai.get_by_store_id(store_id)

        agent = await self._agents.get_by_type(store_id, agent_type)

        provider = (store_cfg.provider if store_cfg else None) or settings.ACTIVE_LLM_PROVIDER

        default_model = (
            store_cfg.default_model
            if store_cfg
            else (settings.OPENAI_MODEL if provider == "openai" else settings.GEMINI_MODEL)
        )

        api_key = self._resolved_api_key(store_cfg)

        if agent is None:
            resolved = ResolvedAgentConfig(
                provider=provider,
                model=default_model,
                temperature=0.7,
                system_prompt=SYSTEM_PROMPT,
                api_key=api_key,
                fallback_used=True,
                agent_id=None,
            )
        else:
            raw_model = (agent.model or "").strip()
            effective_model = raw_model or default_model
            resolved = ResolvedAgentConfig(
                provider=provider,
                model=effective_model,
                temperature=agent.temperature,
                system_prompt=agent.system_prompt,
                api_key=api_key,
                fallback_used=False,
                agent_id=agent.id,
            )

        logger.info(
            "Agent resolved",
            store_id=str(store_id),
            agent_type=agent_type,
            agent_id=str(resolved.agent_id) if resolved.agent_id else None,
            model=resolved.model,
            fallback_used=resolved.fallback_used,
            provider=resolved.provider,
        )
        return resolved

    def _resolved_api_key(self, store_cfg: StoreAIConfig | None) -> str | None:
        """Plaintext key for provider client, or None to use process environment."""
        if not store_cfg or not store_cfg.api_key_encrypted:
            return None
        plain = decrypt_api_key(store_cfg.api_key_encrypted)
        if plain is None:
            logger.warning("store_ai_configs.api_key_encrypted could not be decrypted; using env")
            return None
        return plain if plain else None
