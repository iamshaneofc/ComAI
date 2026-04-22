"""Events API — tenant-scoped (authenticated store only)."""
from uuid import UUID

from fastapi import APIRouter, Request

from app.core.tenant import authenticated_store_id

router = APIRouter()


@router.post("", summary="Ingest event (stub)")
async def ingest_event(request: Request):
    """Stub: when implemented, all writes must use authenticated_store_id(request)."""
    store_id: UUID = authenticated_store_id(request)
    return {"detail": "Events endpoint — coming soon", "store_id": str(store_id)}
