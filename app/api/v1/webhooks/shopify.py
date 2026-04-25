import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.shopify.webhook_handler import verify_and_normalize_webhook
from app.core.database import get_db
from app.modules.products.service import ProductService
from app.modules.stores.service import StoreService

logger = structlog.get_logger(__name__)

router = APIRouter()


def _normalize_shop_domain(raw: str) -> str:
    return raw.strip().lower().rstrip("/")


@router.post("/products/create")
@router.post("/products/update")
async def shopify_product_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Shopify product webhooks.

    Tenant is resolved ONLY from ``X-Shopify-Shop-Domain`` + HMAC (never ``store_id`` query).
    """
    structlog.contextvars.bind_contextvars(flow="webhook")

    shop_domain = (
        request.headers.get("X-Shopify-Shop-Domain")
        or request.headers.get("x-shopify-shop-domain")
        or ""
    )
    shop_domain = _normalize_shop_domain(shop_domain)
    if not shop_domain:
        raise HTTPException(status_code=400, detail="Missing X-Shopify-Shop-Domain header")

    raw_body = await request.body()
    hmac_header = request.headers.get("x-shopify-hmac-sha256") or request.headers.get("X-Shopify-Hmac-Sha256")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    store_service = StoreService(db)
    store = await store_service.get_store_by_shop_domain(shop_domain)
    if store is None:
        raise HTTPException(status_code=404, detail="Unknown shop domain")

    configured_domain, _, webhook_secret = store_service.get_decrypted_shopify_credentials(store)
    configured_domain = _normalize_shop_domain(str(configured_domain or ""))
    if not webhook_secret:
        logger.error("Shopify webhook secret missing or invalid", store_id=str(store.id))
        raise HTTPException(status_code=401, detail="Webhook secret not configured")

    if configured_domain and shop_domain != configured_domain:
        logger.warning(
            "Shopify domain header mismatch",
            header_domain=shop_domain,
            configured_domain=configured_domain,
            store_id=str(store.id),
        )
        raise HTTPException(status_code=403, detail="Shop domain does not match store configuration")

    store_id: UUID = store.id

    try:
        p_create = verify_and_normalize_webhook(raw_body, hmac_header, webhook_secret, payload)
        product_service = ProductService(db)
        await product_service.upsert_product(store_id, p_create)
    except ValueError as e:
        logger.error("Webhook processing error", error=str(e))
        if str(e) == "Invalid signature":
            raise HTTPException(status_code=401, detail="Invalid HMAC signature") from e
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected webhook error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e

    return {"status": "ok"}
