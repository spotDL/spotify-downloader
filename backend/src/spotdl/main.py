"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from spotdl.api.v1 import router as api_v1_router
from spotdl.api.v1.websocket import router as websocket_router
from spotdl.config import get_settings
from spotdl.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()

    # Startup
    # Ensure data directory exists for SQLite
    if settings.database_is_sqlite:
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)

    # Initialize database tables
    await init_db()

    yield

    # Shutdown
    await close_db()


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
