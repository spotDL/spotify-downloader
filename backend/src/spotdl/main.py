"""FastAPI application entry point."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(log_level if settings.debug else logging.WARNING)

    # Reduce noise from third-party libraries in debug mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={logging.getLevelName(log_level)}, env={settings.environment}, debug={settings.debug}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

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
