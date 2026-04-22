"""Auth routes — stub (to be implemented in Sprint 3). Tenant is from X-API-KEY on this router."""
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.tenant import authenticated_store_id

router = APIRouter()


@router.post("/login", summary="Login (stub)")
async def login(request: Request):
    store_id: UUID = authenticated_store_id(request)
    return {"detail": "Auth endpoint — coming soon", "store_id": str(store_id)}


@router.post("/refresh", summary="Refresh token (stub)")
async def refresh(request: Request):
    store_id: UUID = authenticated_store_id(request)
    return {"detail": "Refresh endpoint — coming soon", "store_id": str(store_id)}
