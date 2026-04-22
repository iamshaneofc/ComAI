import structlog

logger = structlog.get_logger(__name__)

class WhatsAppClient:
    async def send_message(self, phone: str, message: str) -> None:
        """
        Simulates sending a real WhatsApp message to an external provider.
        Maintains abstraction cleanly for future real API integration.
        """
        logger.info(f"Sending WhatsApp to {phone}", message_length=len(message))
        print(f"Sending WhatsApp to {phone}: {message}")

    def send_message_sync(self, phone: str, message: str) -> None:
        """
        Synchronous version for Celery workers.
        """
        logger.info(f"Sending WhatsApp to {phone} (SYNC)", message_length=len(message))
        print(f"Worker sending message: {message} to {phone}")
