"""WhatsApp webhook receiver — stub."""
from fastapi import APIRouter, Request

router = APIRouter()


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
async def receive_message(request: Request):
    return {"received": True}
