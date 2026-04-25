"""WhatsApp webhook receiver."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenant import authenticated_store_id
from app.modules.stores.service import StoreService
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.tasks.message_tasks import send_whatsapp_message

router = APIRouter()
logger = structlog.get_logger(__name__)


def _extract_inbound_text_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {}) if isinstance(value, dict) else {}
            phone_number_id = str(metadata.get("phone_number_id") or "").strip()
            for message in value.get("messages", []) if isinstance(value, dict) else []:
                if message.get("type") != "text":
                    continue
                from_phone = str(message.get("from") or "").strip()
                body = str((message.get("text") or {}).get("body") or "").strip()
                if from_phone and body and phone_number_id:
                    extracted.append(
                        {
                            "store_phone_number_id": phone_number_id,
                            "from_phone": from_phone,
                            "body": body,
                        }
                    )
    return extracted


@router.get("", summary="WhatsApp webhook verification")
async def verify_webhook(
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
):
    """Meta requires a GET endpoint to verify the webhook URL."""
    from app.core.config import settings
    if hub_mode == "subscribe" and hub_verify_token == settings.META_WEBHOOK_VERIFY_TOKEN:
        return int(hub_challenge) if hub_challenge else 0
    return {"detail": "Verification failed"}


@router.post("", summary="Receive WhatsApp messages (stub)")
async def receive_message(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = await request.json()
    inbound_messages = _extract_inbound_text_messages(payload)

    processed = 0
    queued = 0
    for msg in inbound_messages:
        store = await StoreService(db).get_store_by_whatsapp_phone_number(msg["store_phone_number_id"])
        if not store:
            logger.warning(
                "WhatsApp inbound ignored: unknown phone number id",
                phone_number_id=msg["store_phone_number_id"],
            )
            continue

        chat_service = ChatService(db)
        chat_resp = await chat_service.handle_chat(
            store_id=store.id,
            payload=ChatRequest(session_id=msg["from_phone"], message=msg["body"]),
        )
        processed += 1
        try:
            send_whatsapp_message.apply_async(
                args=(msg["from_phone"], chat_resp.message),
                retry=False,
            )
            queued += 1
        except Exception as exc:
            logger.error(
                "Failed to enqueue WhatsApp outbound reply",
                store_id=str(store.id),
                to=msg["from_phone"],
                error=str(exc),
            )

    return {"received": True, "processed": processed, "queued_replies": queued}
