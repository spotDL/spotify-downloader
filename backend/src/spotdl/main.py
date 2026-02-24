"""FastAPI application entry point."""

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from spotdl.api.v1 import router as api_v1_router
from spotdl.api.v1.websocket import router as websocket_router
from spotdl.config import get_settings
from spotdl.core.security import initialize_token_blacklist
from spotdl.db.database import close_db, get_db, init_db


def setup_logging() -> None:
    """Configure logging based on environment settings."""
    settings = get_settings()

    # Determine log level - explicit setting takes priority
    if settings.log_level:
        log_level = getattr(logging, settings.log_level)
    elif settings.debug:
        log_level = logging.DEBUG
    elif settings.is_development:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )

    # Set specific loggers
    logging.getLogger("spotdl").setLevel(log_level)
    logging.getLogger("spotdl.api").setLevel(log_level)  # API request logging
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.error").setLevel(log_level)
    # Always show access logs in development
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if settings.is_development else logging.WARNING)

    # Reduce noise from third-party libraries in debug mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={logging.getLevelName(log_level)}, env={settings.environment}, debug={settings.debug}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Configure logging first
    setup_logging()

    settings = get_settings()
    logger = logging.getLogger(__name__)

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.debug(f"Database URL: {settings.database_url}")

    # Ensure data directory exists for SQLite
    if settings.database_is_sqlite:
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)

    # Initialize database tables
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    # Initialize token blacklist cache from database
    logger.info("Initializing token blacklist cache...")
    async with get_db() as db:
        token_count = await initialize_token_blacklist(db)
        logger.info(f"Token blacklist cache initialized with {token_count} tokens")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Shutdown complete")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs request method, path, status code, and response time.
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request and log details."""
        logger = logging.getLogger("spotdl.api")

        # Skip logging for health check and static files
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)

        start_time = time.time()

        # Log incoming request
        logger.debug("→ %s %s", request.method, request.url.path)

        # Process the request
        response = await call_next(request)

        # Calculate response time
        duration = (time.time() - start_time) * 1000  # Convert to ms

        # Log response with status code
        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING

        logger.log(
            log_level,
            "← %s %s → %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )

        return response


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler that logs all unhandled exceptions with full traceback.

    This catches any exception that wasn't handled by endpoint-specific handlers.
    """
    logger = logging.getLogger(__name__)

    # Log the full exception with traceback
    logger.error(
        "Unhandled exception during request to %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    # Return a generic error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error. Please try again later.",
            "type": type(exc).__name__,
        },
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-platform music matching and download API",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Register global exception handler
    app.add_exception_handler(Exception, global_exception_handler)

    # Request logging middleware (must be added before other middleware)
    app.add_middleware(RequestLoggingMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    @app.get("/health")
    async def root_health_check():
        """Infrastructure-friendly liveness endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.now(UTC),
        }

    # Include API routers
    app.include_router(api_v1_router)

    # Include WebSocket router
    app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])

    # Mount static files for React frontend (if exists)
    static_path = Path("./static")
    if static_path.exists() and static_path.is_dir():
        app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

    return app


# Application instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "spotdl.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )
