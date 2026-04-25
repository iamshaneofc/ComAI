"""
API v1 Router — aggregates all sub-routers under /api/v1.

All business routes require X-API-KEY except:
    - POST /stores (requires X-Provision-Secret = APP_SECRET_KEY)
    - GET /platform/stores, DELETE /platform/stores/{id} (same; dev-console tenant listing / soft-delete)
    - Webhooks (Shopify HMAC / Meta verification)
"""
from fastapi import APIRouter, Depends

from app.api.dependencies import resolve_rate_limit, verify_store_api_key
from app.api.v1 import agents, ai_config, analytics, auth, chat, events, health, orders, platform, products, stores
from app.api.v1.webhooks import shopify, whatsapp

v1_router = APIRouter()

# --- Webhooks (NOT tenant API key) ---
v1_router.include_router(shopify.router, prefix="/webhooks/shopify", tags=["Webhooks"])
v1_router.include_router(whatsapp.router, prefix="/webhooks/whatsapp", tags=["Webhooks"])

# --- Store provisioning (platform secret, not tenant API key) ---
v1_router.include_router(stores.provision_router, prefix="/stores", tags=["Stores"])

# --- Platform / dev console (X-Provision-Secret only; never expose publicly) ---
v1_router.include_router(platform.router, prefix="/platform", tags=["Platform"])

# --- Authenticated tenant API (X-API-KEY → request.state.store) ---
protected = APIRouter(dependencies=[Depends(verify_store_api_key)])

protected.include_router(health.router, tags=["Health"])
protected.include_router(auth.router, prefix="/auth", tags=["Authentication"])
protected.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat (AI)"],
    dependencies=[Depends(resolve_rate_limit)],
)
protected.include_router(products.router, prefix="/products", tags=["Products"])
protected.include_router(orders.router, prefix="/orders", tags=["Orders"])
protected.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
protected.include_router(stores.tenant_router, prefix="/stores", tags=["Stores"])
protected.include_router(events.router, prefix="/events", tags=["Events"])
protected.include_router(agents.router, prefix="/agents", tags=["Agents"])
protected.include_router(ai_config.router, prefix="/ai-config", tags=["AI Config"])

v1_router.include_router(protected)
