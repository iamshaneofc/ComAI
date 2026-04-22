from app.core.celery_app import celery_app
from app.channels.whatsapp.service import WhatsAppService

@celery_app.task(bind=True, max_retries=3)
def send_whatsapp_message(self, phone, message):
    try:
        WhatsAppService().send_message_sync(phone, message)
    except Exception as e:
        raise self.retry(exc=e, countdown=5)
