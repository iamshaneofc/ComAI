"""
CRUD for tenant-scoped Agent rows (management API).

Enforces at most one active agent per (store_id, type) by deactivating siblings when activating.
"""
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.agent import Agent
from app.repositories.agent_repo import AgentRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.store_ai_config_repo import StoreAIConfigRepository
from app.repositories.store_repo import StoreRepository
from app.schemas.agent import (
    AgentChatConfigResponse,
    AgentChatPatch,
    AgentCreate,
    AgentResponse,
    AgentUpdate,
)
from app.services.prompt_generator_service import PromptGeneratorService
from app.services.store_context_service import StoreContextService

logger = structlog.get_logger(__name__)


class AgentManagementService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self._agents = AgentRepository(db)
        self._store_ai = StoreAIConfigRepository(db)

    async def _effective_default_model(self, store_id: UUID) -> str:
        row = await self._store_ai.get_by_store_id(store_id)
        if row:
            return row.default_model
        prov = settings.ACTIVE_LLM_PROVIDER
        return settings.OPENAI_MODEL if prov == "openai" else settings.GEMINI_MODEL

    async def _build_chat_prompt_for_store(
        self,
        store_id: UUID,
        *,
        tone: str,
        goal: str,
        language: str | None,
    ) -> str:
        store_repo = StoreRepository(self.db)
        store = await store_repo.get_by_id(store_id)
        store_name = store.name if store else "Our store"
        products = ProductRepository(self.db)
        cats = await products.sample_product_categories(store_id)
        context_service = StoreContextService(self.db)
        prompt_context = await context_service.get_prompt_context(store_id)
        return PromptGeneratorService.build_chat_system_prompt(
            store_name=store_name,
            product_categories=cats,
            tone=tone,
            industry_hint=None,
            goal=goal,
            language=language,
            policies=prompt_context.get("policies"),
            faqs=prompt_context.get("faqs"),
            tone_hint=prompt_context.get("tone_hint"),
        )

    async def create_agent(self, store_id: UUID, payload: AgentCreate) -> AgentResponse:
        raw_model = (payload.model or "").strip()
        model_value = raw_model or await self._effective_default_model(store_id)
        lang = (
            payload.language.strip()
            if payload.language and payload.language.strip()
            else None
        )

        agent = Agent(
            store_id=store_id,
            name=payload.name,
            type=payload.type,
            model=model_value,
            system_prompt=payload.system_prompt,
            temperature=payload.temperature,
            is_active=payload.is_active,
            tone=payload.tone,
            goal=payload.goal,
            language=lang,
        )
        self.db.add(agent)
        await self.db.flush()
        if payload.is_active:
            await self._agents.deactivate_others_same_type(store_id, payload.type, agent.id)
        await self.db.refresh(agent)
        logger.info("Agent created", store_id=str(store_id), agent_id=str(agent.id), agent_type=agent.type)
        return AgentResponse.model_validate(agent)

    async def list_agents(self, store_id: UUID, *, active_only: bool = False) -> list[AgentResponse]:
        rows = await self._agents.list_for_store(store_id, active_only=active_only)
        return [AgentResponse.model_validate(r) for r in rows]

    async def get_agent(self, store_id: UUID, agent_id: UUID) -> AgentResponse:
        agent = await self._agents.get_by_id_for_store(store_id, agent_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return AgentResponse.model_validate(agent)

    async def get_chat_agent_config(self, store_id: UUID) -> AgentChatConfigResponse:
        agent = await self._agents.get_by_type(store_id, "chat")
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active chat agent. Complete store onboarding or PATCH /agents/chat to create one.",
            )
        return AgentChatConfigResponse.model_validate(agent)

    async def patch_chat_agent_config(self, store_id: UUID, patch: AgentChatPatch) -> AgentChatConfigResponse:
        fs = patch.model_fields_set
        agent = await self._agents.get_by_type(store_id, "chat")

        if agent is None:
            tone = patch.tone if "tone" in fs and patch.tone is not None else "friendly"
            goal = patch.goal if "goal" in fs and patch.goal is not None else "sales"
            language: str | None = None
            if "language" in fs:
                language = (
                    patch.language.strip()
                    if patch.language and str(patch.language).strip()
                    else None
                )
            name = patch.name if "name" in fs and patch.name else "Shop Assistant"
            raw_model = patch.model if "model" in fs else None
            model_val = (raw_model or "").strip() if raw_model is not None else ""
            model_val = model_val or await self._effective_default_model(store_id)
            temp = (
                float(patch.temperature)
                if "temperature" in fs and patch.temperature is not None
                else 0.7
            )
            prompt = await self._build_chat_prompt_for_store(
                store_id, tone=tone, goal=goal, language=language
            )
            agent = Agent(
                store_id=store_id,
                name=name,
                type="chat",
                model=model_val,
                system_prompt=prompt,
                temperature=temp,
                is_active=True,
                tone=tone,
                goal=goal,
                language=language,
            )
            self.db.add(agent)
            await self.db.flush()
            await self._agents.deactivate_others_same_type(store_id, "chat", agent.id)
            await self.db.refresh(agent)
            logger.info("Chat agent created via PATCH", store_id=str(store_id), agent_id=str(agent.id))
            return AgentChatConfigResponse.model_validate(agent)

        if patch.name is not None:
            agent.name = patch.name
        if patch.tone is not None:
            agent.tone = patch.tone
        if patch.goal is not None:
            agent.goal = patch.goal
        if "language" in fs:
            if patch.language is None or (
                isinstance(patch.language, str) and not patch.language.strip()
            ):
                agent.language = None
            else:
                agent.language = patch.language.strip()
        if patch.model is not None:
            raw = (patch.model or "").strip()
            agent.model = raw or await self._effective_default_model(store_id)
        if patch.temperature is not None:
            agent.temperature = patch.temperature

        agent.system_prompt = await self._build_chat_prompt_for_store(
            store_id,
            tone=agent.tone,
            goal=agent.goal,
            language=agent.language,
        )

        await self.db.flush()
        if agent.is_active:
            await self._agents.deactivate_others_same_type(store_id, "chat", agent.id)
        await self.db.refresh(agent)
        logger.info("Chat agent config updated", store_id=str(store_id), agent_id=str(agent.id))
        return AgentChatConfigResponse.model_validate(agent)

    async def update_agent(self, store_id: UUID, agent_id: UUID, payload: AgentUpdate) -> AgentResponse:
        agent = await self._agents.get_by_id_for_store(store_id, agent_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        fs_update = payload.model_fields_set

        if payload.name is not None:
            agent.name = payload.name
        if payload.type is not None:
            agent.type = payload.type
        if payload.model is not None:
            raw = (payload.model or "").strip()
            agent.model = raw or await self._effective_default_model(store_id)
        if payload.system_prompt is not None:
            agent.system_prompt = payload.system_prompt
        if payload.temperature is not None:
            agent.temperature = payload.temperature
        if payload.is_active is not None:
            agent.is_active = payload.is_active
        if payload.tone is not None:
            agent.tone = payload.tone
        if payload.goal is not None:
            agent.goal = payload.goal
        if "language" in fs_update:
            if payload.language is None or (
                isinstance(payload.language, str) and not str(payload.language).strip()
            ):
                agent.language = None
            else:
                agent.language = str(payload.language).strip()

        await self.db.flush()
        if agent.is_active:
            await self._agents.deactivate_others_same_type(store_id, agent.type, agent.id)
        await self.db.refresh(agent)
        logger.info("Agent updated", store_id=str(store_id), agent_id=str(agent.id), agent_type=agent.type)
        return AgentResponse.model_validate(agent)

    async def deactivate_agent(self, store_id: UUID, agent_id: UUID) -> None:
        agent = await self._agents.get_by_id_for_store(store_id, agent_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        agent.is_active = False
        await self.db.flush()
        logger.info("Agent deactivated", store_id=str(store_id), agent_id=str(agent.id))
