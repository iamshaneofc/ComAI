from fastapi import APIRouter, Depends, Request, status

from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics_service import AnalyticsService
from app.tasks.onboarding_tasks import sync_store_products_task

router = APIRouter()


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Owner dashboard analytics overview",
)
async def analytics_overview(
    request: Request,
    service: AnalyticsService = Depends(AnalyticsService),
) -> AnalyticsOverviewResponse:
    return await service.get_overview(request.state.store.id)


@router.post(
    "/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger analytics refresh via store sync pipeline",
)
async def analytics_sync(request: Request):
    sid = request.state.store.id
    sync_store_products_task.apply_async(args=(str(sid),), retry=False)
    return {"status": "sync_queued", "store_id": str(sid)}
