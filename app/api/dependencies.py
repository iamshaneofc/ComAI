import time
from collections import defaultdict
import structlog
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.store import Store

logger = structlog.get_logger(__name__)
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# Basic in-memory rate limiter
# { "store_id:user_id": [(timestamp1), (timestamp2)] }
_rate_limits: dict[str, list[float]] = defaultdict(list)

async def verify_store_api_key(request: Request, api_key: str = Security(api_key_header), db: AsyncSession = Depends(get_db)) -> Store:
    """Authenticates API Key against Stores and binds into state/log context."""
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-KEY header missing")
    
    result = await db.execute(select(Store).where(Store.api_key == api_key, Store.is_active == True))
    store = result.scalar_one_or_none()
    
    if not store:
        logger.warning("Invalid API Key attempted", api_key=api_key[:5] + "...")
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    request.state.store = store
    request.state.store_id = store.id
    
    # Inject structlog properties globally
    structlog.contextvars.bind_contextvars(store_id=str(store.id))
    return store

async def resolve_rate_limit(request: Request, store: Store = Depends(verify_store_api_key)):
    """Enforces 20 requests per minute per user per store on endpoints."""
    # Attempt to extract session parsing without body logic
    # In chat, session_id is in body normally, but rate limiter happens before body.
    # To limit properly, we can limit based on IP instead if session_id is body only
    user_id = request.client.host if request.client else "unknown"
    key = f"{store.id}:{user_id}"
    
    now = time.time()
    # Filter valid timestamps within 60 seconds
    valid_times = [t for t in _rate_limits[key] if now - t < 60]
    
    if len(valid_times) >= 20: # 20 requests per minute ceiling
        logger.warning("Rate limit exceeded", store_id=str(store.id), identity=user_id)
        raise HTTPException(status_code=429, detail="Too many requests")
        
    valid_times.append(now)
    _rate_limits[key] = valid_times
