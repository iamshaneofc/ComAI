"""Events routes — stub (to be implemented in Sprint 5)."""
from fastapi import APIRouter

router = APIRouter()


@router.post("", summary="Ingest event (stub)")
async def ingest_event():
    return {"detail": "Events endpoint — coming soon"}
