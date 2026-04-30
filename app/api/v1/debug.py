"""
Debug API routes for internal verification.

Not for production public exposure.
"""
from fastapi import APIRouter, Depends, Query, Request

from app.repositories.chat_message_repo import ChatMessageRepository
from app.schemas.debug import DebugChatMessage
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/chat-messages",
    response_model=list[DebugChatMessage],
    summary="Debug: inspect persisted chat messages for a session",
    description="Not for production public exposure",
)
async def get_debug_chat_messages(
    request: Request,
    session_id: str = Query(..., min_length=1, description="Conversation session id"),
    limit: int = Query(10, ge=1, le=50, description="Max records, capped at 50"),
    db: AsyncSession = Depends(get_db),
) -> list[DebugChatMessage]:
    store_id = request.state.store.id
    repo = ChatMessageRepository(db)
    rows = await repo.get_recent_messages(store_id=store_id, session_id=session_id, limit=limit)
    # Tenant safety check: repository already scopes by store_id; keep explicit guard anyway.
    safe_rows = [r for r in rows if r.store_id == store_id]
    return [
        DebugChatMessage(
            role=r.role,
            message=r.content,
            timestamp=r.created_at,
        )
        for r in safe_rows
    ]
