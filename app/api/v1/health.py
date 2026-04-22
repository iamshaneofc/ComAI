"""
Health Check Endpoints — no auth required.

GET /health  → liveness probe (is the process alive?)
GET /ready   → readiness probe (can we serve traffic?)
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.get("/health", summary="Liveness probe")
async def health():
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready(db: AsyncSession = Depends(get_db)):
    """Checks DB connectivity before marking as ready."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
