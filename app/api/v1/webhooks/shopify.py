import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.shopify.webhook_handler import verify_and_normalize_webhook
from app.modules.stores.service import StoreService
from app.modules.products.service import ProductService
from app.core.database import get_db
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/products/create")
@router.post("/products/update")
async def shopify_product_webhook(
    request: Request,
    store_id: UUID | None = None, # It can be retrieved via query params if generic, but instructions were just webhooks/shopify/products. We simulate store validation via query parameter here or dynamic path extraction. If not provided it will error. Wait! The prompt endpoint didn't specify store_id specifically in the path for webhook POST. Assuming query parameter.
    db: AsyncSession = Depends(get_db)
):
    structlog.contextvars.bind_contextvars(flow="webhook")
    if not store_id:
        store_id_str = request.query_params.get("store_id")
        if store_id_str:
            store_id = UUID(store_id_str)
        else:
            raise HTTPException(status_code=400, detail="store_id query param is required")

    raw_body = await request.body()
    hmac_header = request.headers.get("x-shopify-hmac-sha256") or request.headers.get("X-Shopify-Hmac-Sha256")
    
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    store_service = StoreService(db)
    try:
        store = await store_service.get_store(store_id)
    except HTTPException as e:
        raise e
        
    creds = store.credentials.get("shopify", {}) if store.credentials else {}
    webhook_secret = creds.get("webhook_secret")
        
    try:
        # Adapter purely normalizes and validates signature
        p_create = verify_and_normalize_webhook(raw_body, hmac_header, webhook_secret, payload)
        
        # Service handles DB orchestration
        product_service = ProductService(db)
        await product_service.upsert_product(store_id, p_create)
        
    except ValueError as e:
        logger.error(f"Webhook processing error: {e}")
        if str(e) == "Invalid signature":
            raise HTTPException(status_code=401, detail="Invalid HMAC signature")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"status": "ok"}
