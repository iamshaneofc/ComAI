"""
Resolve per-store, per-channel LLM configuration (Agent + StoreAIConfig) with safe fallbacks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt.builder import SYSTEM_PROMPT
from app.core.config import settings
from app.core.field_crypto import decrypt_api_key
from app.models.agent import Agent
from app.models.store_ai_config import StoreAIConfig

logger = structlog.get_logger(__name__)

AgentType = Literal["chat", "whatsapp", "call"]


@dataclass(frozen=True, slots=True)
class ResolvedAgentConfig:
    """Runtime LLM settings after DB resolution (secrets never logged)."""

    provider: str
    model: str
    temperature: float
    system_prompt: str
    api_key: str | None
    fallback_used: bool


class AgentResolver:
    """Loads StoreAIConfig and active Agent for (store_id, agent_type)."""

    async def resolve(
        self,
        db: AsyncSession,
        store_id: UUID,
        agent_type: AgentType,
    ) -> ResolvedAgentConfig:
        store_cfg = (
            await db.execute(select(StoreAIConfig).where(StoreAIConfig.store_id == store_id))
        ).scalar_one_or_none()

        agent_rows = (
            (
                await db.execute(
                    select(Agent)
                    .where(
                        Agent.store_id == store_id,
                        Agent.type == agent_type,
                        Agent.is_active.is_(True),
                    )
                    .order_by(Agent.updated_at.desc())
                )
            )
            .scalars()
            .all()
        )

        if len(agent_rows) > 1:
            logger.warning(
                "Multiple active agents for store/type; using most recently updated",
                store_id=str(store_id),
                agent_type=agent_type,
                count=len(agent_rows),
            )

        agent = agent_rows[0] if agent_rows else None

        provider = (store_cfg.provider if store_cfg else None) or settings.ACTIVE_LLM_PROVIDER

        default_model = (
            store_cfg.default_model
            if store_cfg
            else (settings.OPENAI_MODEL if provider == "openai" else settings.GEMINI_MODEL)
        )

        if agent is None:
            return ResolvedAgentConfig(
                provider=provider,
                model=default_model,
                temperature=0.7,
                system_prompt=SYSTEM_PROMPT,
                api_key=self._resolved_api_key(store_cfg, provider),
                fallback_used=True,
            )

        model = agent.model or default_model
        api_key = self._resolved_api_key(store_cfg, provider)

        return ResolvedAgentConfig(
            provider=provider,
            model=model,
            temperature=agent.temperature,
            system_prompt=agent.system_prompt,
            api_key=api_key,
            fallback_used=False,
        )

    def _resolved_api_key(self, store_cfg: StoreAIConfig | None, provider: str) -> str | None:
        """Plaintext key for provider client, or None to use process environment."""
        if not store_cfg or not store_cfg.api_key_encrypted:
            return None
        plain = decrypt_api_key(store_cfg.api_key_encrypted)
        if plain is None:
            logger.warning("store_ai_configs.api_key_encrypted could not be decrypted; using env")
            return None
        return plain if plain else None
