import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class WhatsAppClient:
    def _endpoint(self) -> str:
        if not settings.META_PHONE_NUMBER_ID:
            raise RuntimeError("META_PHONE_NUMBER_ID is not configured")
        return f"https://graph.facebook.com/v20.0/{settings.META_PHONE_NUMBER_ID}/messages"

    def _headers(self) -> dict[str, str]:
        if not settings.META_ACCESS_TOKEN:
            raise RuntimeError("META_ACCESS_TOKEN is not configured")
        return {
            "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    def _payload(self, to: str, message: str) -> dict:
        return {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }

    async def send_message(self, to: str, message: str) -> None:
        logger.info("Sending WhatsApp message", recipient=to, message_length=len(message))
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self._endpoint(),
                headers=self._headers(),
                json=self._payload(to, message),
            )
            response.raise_for_status()

    def send_message_sync(self, to: str, message: str) -> None:
        logger.info("Sending WhatsApp message (sync)", recipient=to, message_length=len(message))
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                self._endpoint(),
                headers=self._headers(),
                json=self._payload(to, message),
            )
            response.raise_for_status()
