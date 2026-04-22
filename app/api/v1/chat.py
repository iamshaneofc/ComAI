"""
Chat API Route — POST /chat

Phase 1 design:
    - No auth required (demo / investor pitch friendly)
    - store_id passed in the request body
    - Thin route: validate → service → respond
"""
from fastapi import APIRouter, Depends, Request

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.api.dependencies import resolve_rate_limit

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
    """
    Send a message to the AI shopping assistant.

    **Demo flow:**
    1. POST with `store_id` + `message`
    2. AI detects intent (product search, greeting, support)
    3. Fetches relevant products from the store's catalogue
    4. Builds contextual prompt + calls OpenAI
    5. Returns AI reply + product cards

    **Example inputs:**
    - `"Shoes under 3000"` → product_search + matching products
    - `"Hi there"` → greeting (no LLM call)
    - `"Track my order"` → support response
    """
    return await service.handle_chat(
        store_id=request.state.store_id,
        payload=payload,
    )
