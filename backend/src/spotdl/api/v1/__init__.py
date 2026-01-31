"""API v1 endpoints."""

from fastapi import APIRouter

from spotdl.api.v1 import health

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
