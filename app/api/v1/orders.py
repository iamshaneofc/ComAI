"""Orders API — tenant-scoped (authenticated store only)."""
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.tenant import authenticated_store_id

router = APIRouter()


@router.get("", summary="List orders (stub)")
async def list_orders(request: Request):
    store_id: UUID = authenticated_store_id(request)
    return {"detail": "Orders endpoint — coming soon", "store_id": str(store_id)}
