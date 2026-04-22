from app.channels.whatsapp.client import WhatsAppClient

class WhatsAppService:
    def __init__(self):
        self.client = WhatsAppClient()

    async def send_product_recommendation(self, user, products: list) -> None:
        if not getattr(user, "phone", None):
            return

        lines = ["Hey! Based on your interest, check these out:"]
        for i, p in enumerate(products, 1):
            # p can be a Dict or ORM object depending on mapping
            title = getattr(p, "title", p.get("title") if isinstance(p, dict) else "Product")
            price = getattr(p, "price", p.get("price") if isinstance(p, dict) else "0")
            lines.append(f"{i}. {title} - ₹{price}")

        message = "\n".join(lines)
        await self.client.send_message(user.phone, message)
