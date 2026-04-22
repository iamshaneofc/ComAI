"""
AI Commerce Platform — FastAPI Application Entry Point (Revised for Sprint 2)

Changes from Sprint 1:
- Added global exception handlers (ValueError → 400, generic → 500)
- Added startup DB connectivity check
- Router imports cleaned up (only real routes)
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse

from app.api.v1.router import v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware, TenantResolverMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup → yield → shutdown."""
    configure_logging()
    logger.info(
        "AI Commerce Platform starting",
        env=settings.APP_ENV,
        debug=settings.APP_DEBUG,
    )

    # Verify DB connectivity at startup (fail fast)
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        raise

    yield

    logger.info("AI Commerce Platform shutting down")
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Multi-tenant AI-powered ecommerce backend",
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ----------------------------------------------------------------
    # Middleware (outermost first)
    # ----------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantResolverMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ----------------------------------------------------------------
    # Global Exception Handlers
    # ----------------------------------------------------------------

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": str(exc),
                    "details": {}
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "details": {}
                }
            },
        )

    # ----------------------------------------------------------------
    # Routers
    # ----------------------------------------------------------------
    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
