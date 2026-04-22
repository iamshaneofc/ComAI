"""Auth routes — stub (to be implemented in Sprint 3)."""
from fastapi import APIRouter

router = APIRouter()


@router.post("/login", summary="Login (stub)")
async def login():
    return {"detail": "Auth endpoint — coming soon"}


@router.post("/refresh", summary="Refresh token (stub)")
async def refresh():
    return {"detail": "Refresh endpoint — coming soon"}
