from datetime import datetime

from pydantic import BaseModel


class AnalyticsMetric(BaseModel):
    key: str
    value: dict
    updated_at: datetime


class AnalyticsOverviewResponse(BaseModel):
    items: list[AnalyticsMetric]
