"""
Agents API — tenant-scoped CRUD. Store is always ``request.state.store`` (X-API-KEY).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.tenant import authenticated_store_id
from app.schemas.agent import (
    AgentChatConfigResponse,
    AgentChatPatch,
    AgentCreate,
    AgentResponse,
    AgentUpdate,
)
from app.services.agent_management_service import AgentManagementService

router = APIRouter()


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent",
)
async def create_agent(
    payload: AgentCreate,
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> AgentResponse:
    return await service.create_agent(store_id, payload)


@router.get(
    "",
    response_model=list[AgentResponse],
    summary="List agents for this store",
)
async def list_agents(
    active_only: bool = Query(False, description="If true, only is_active=true rows"),
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> list[AgentResponse]:
    return await service.list_agents(store_id, active_only=active_only)


@router.get(
    "/chat",
    response_model=AgentChatConfigResponse,
    summary="Get active chat agent behaviour and generated system prompt",
)
async def get_chat_agent(
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> AgentChatConfigResponse:
    return await service.get_chat_agent_config(store_id)


@router.patch(
    "/chat",
    response_model=AgentChatConfigResponse,
    summary="Update chat agent behaviour and regenerate system_prompt",
)
async def patch_chat_agent(
    payload: AgentChatPatch,
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> AgentChatConfigResponse:
    return await service.patch_chat_agent_config(store_id, payload)


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get one agent",
)
async def get_agent(
    agent_id: UUID,
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> AgentResponse:
    return await service.get_agent(store_id, agent_id)


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update an agent",
)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> AgentResponse:
    return await service.update_agent(store_id, agent_id, payload)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate an agent (soft delete)",
)
async def delete_agent(
    agent_id: UUID,
    store_id: UUID = Depends(authenticated_store_id),
    service: AgentManagementService = Depends(AgentManagementService),
) -> None:
    await service.deactivate_agent(store_id, agent_id)
