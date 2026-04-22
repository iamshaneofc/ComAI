"""
Chat API — POST /chat

Tenant is always `request.state.store` from X-API-KEY (never from headers/body).
"""
from fastapi import APIRouter, Depends, Request

from app.api.dependencies import resolve_rate_limit
from app.core.tenant import authenticated_store_id
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with AI shopping assistant",
    dependencies=[Depends(resolve_rate_limit)]
)
async def chat(
    request: Request,
    payload: ChatRequest,
    service: ChatService = Depends(ChatService),
) -> ChatResponse:
    """Send a message to the AI assistant for the authenticated store."""
    return await service.handle_chat(
        store_id=authenticated_store_id(request),
        payload=payload,
    )
