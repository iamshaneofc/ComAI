"""
API v1 Router — aggregates all sub-routers under /api/v1.

Rules:
    - No business logic here
    - Only import and include sub-routers
    - Tag groups for OpenAPI docs
"""
from fastapi import APIRouter, Depends

from app.api.v1 import auth, chat, events, health, orders, products, stores
from app.api.v1.webhooks import shopify, whatsapp
from app.api.dependencies import verify_store_api_key

v1_router = APIRouter()

# --- Core ---
v1_router.include_router(health.router, tags=["Health"])
# External auth router could also have API Key check or generic auth, we'll enforce it too
v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"], dependencies=[Depends(verify_store_api_key)])

# --- Business (Protected) ---
protected_deps = [Depends(verify_store_api_key)]
v1_router.include_router(chat.router, prefix="/chat", tags=["Chat (AI)"], dependencies=protected_deps)
v1_router.include_router(products.router, prefix="/products", tags=["Products"], dependencies=protected_deps)
v1_router.include_router(orders.router, prefix="/orders", tags=["Orders"], dependencies=protected_deps)
v1_router.include_router(stores.router, prefix="/stores", tags=["Stores"], dependencies=protected_deps)
v1_router.include_router(events.router, prefix="/events", tags=["Events"], dependencies=protected_deps)

# --- Webhooks ---
v1_router.include_router(shopify.router, prefix="/webhooks/shopify", tags=["Webhooks"])
v1_router.include_router(whatsapp.router, prefix="/webhooks/whatsapp", tags=["Webhooks"])
