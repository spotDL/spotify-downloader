"""Admin API endpoints."""

from fastapi import APIRouter

from spotdl.api.v1.admin.data import router as data_router
from spotdl.api.v1.admin.matches import router as matches_router
from spotdl.api.v1.admin.stats import router as stats_router
from spotdl.api.v1.admin.users import router as users_router

router = APIRouter(prefix="/admin")
router.include_router(users_router)
router.include_router(stats_router)
router.include_router(matches_router)
router.include_router(data_router)
