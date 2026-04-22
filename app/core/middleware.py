"""
Request ID and Tenant Resolver Middleware.

RequestIDMiddleware:
    - Assigns a unique request ID to every incoming request
    - Adds it to response headers and logging context

TenantResolverMiddleware:
    - Reads X-Store-ID header (or JWT claim) and stores in request state
    - ALL downstream handlers can access request.state.store_id
"""
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID into every request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """
    Resolves the store_id (tenant) from the X-Store-ID header.

    In production, this should also validate the store_id against
    the authenticated user's allowed stores (done in service layer).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        store_id_raw = request.headers.get("X-Store-ID")
        if store_id_raw:
            try:
                request.state.store_id = uuid.UUID(store_id_raw)
            except ValueError:
                request.state.store_id = None
        else:
            request.state.store_id = None

        structlog.contextvars.bind_contextvars(store_id=str(request.state.store_id))
        return await call_next(request)
