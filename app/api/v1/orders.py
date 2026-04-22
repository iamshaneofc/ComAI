"""Orders routes — stub (to be implemented in Sprint 4)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="List orders (stub)")
async def list_orders():
    return {"detail": "Orders endpoint — coming soon"}
