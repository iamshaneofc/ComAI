import time

import structlog
from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.store import Store
from app.repositories.store_repo import StoreRepository

logger = structlog.get_logger(__name__)
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def verify_store_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Store:
    """Authenticates API Key against Stores and binds into state/log context."""
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-KEY header missing")

    repo = StoreRepository(db)
    store = await repo.get_by_api_key(api_key)

    if not store:
        logger.warning("Invalid API Key attempted", api_key_prefix=(api_key[:4] + "…") if api_key else "")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    request.state.store = store
    request.state.store_id = store.id

    structlog.contextvars.bind_contextvars(store_id=str(store.id))
    return store


def verify_provision_secret(
    x_provision_secret: str | None = Header(None, alias="X-Provision-Secret"),
) -> None:
    """Bootstrap-only: create initial store using shared platform secret (APP_SECRET_KEY)."""
    if not x_provision_secret or x_provision_secret != settings.APP_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Provision-Secret")


async def resolve_rate_limit(request: Request) -> None:
    """Per-tenant + client IP fixed window limit using Redis (falls back open if Redis unavailable)."""
    store = getattr(request.state, "store", None)
    if store is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    window = int(time.time() // 60)
    identity = request.client.host if request.client else "unknown"
    key = f"rl:v1:{store.id}:{identity}:{window}"
    try:
        r = await get_redis()
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, 120)
        if n > 20:
            logger.warning("Rate limit exceeded", store_id=str(store.id), identity=identity)
            raise HTTPException(status_code=429, detail="Too many requests")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Rate limiter degraded (Redis error); allowing request", error=str(exc))
