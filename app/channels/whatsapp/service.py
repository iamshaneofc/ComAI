from app.channels.whatsapp.client import WhatsAppClient

class WhatsAppService:
    def __init__(self):
        self.client = WhatsAppClient()

    def send_message_sync(self, phone: str, message: str) -> None:
        """Synchronous sending for workers."""
        self.client.send_message_sync(phone, message)

    def generate_recommendation_message(self, products: list) -> str:
        lines = ["Hey! Based on your interest, check these out:"]
        for i, p in enumerate(products, 1):
            title = getattr(p, "title", p.get("title") if isinstance(p, dict) else "Product")
            price = getattr(p, "price", p.get("price") if isinstance(p, dict) else "0")
            lines.append(f"{i}. {title} - ₹{price}")
        return "\n".join(lines)

    async def send_product_recommendation(self, user, products: list) -> None:
        if not getattr(user, "phone", None):
            return

        message = self.generate_recommendation_message(products)
        await self.client.send_message(user.phone, message)
