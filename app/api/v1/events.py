"""Events API — tenant-scoped behavioral event ingestion."""
from fastapi import APIRouter, Depends

from app.core.tenant import authenticated_store_id
from app.schemas.event import EventIngestRequest, EventIngestResponse
from app.services.memory_service import MemoryService

router = APIRouter()


@router.post("", response_model=EventIngestResponse, summary="Ingest behavioral event")
async def ingest_event(
    payload: EventIngestRequest,
    store_id=Depends(authenticated_store_id),
    service: MemoryService = Depends(MemoryService),
) -> EventIngestResponse:
    event = await service.track_event(
        store_id=store_id,
        user_id=payload.user_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    return EventIngestResponse(
        id=event.id,
        user_id=event.user_id,
        event_type=event.event_type,
    )
