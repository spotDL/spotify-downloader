"""API v1 endpoints."""

from fastapi import APIRouter

from spotdl.api.v1 import (
    admin,
    auth,
    download,
    entities,
    health,
    lyrics,
    matches,
    providers,
    reports,
    search,
    settings,
    songs,
    votes,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, tags=["auth"])
router.include_router(songs.router, tags=["songs"])
router.include_router(search.router, tags=["search"])
router.include_router(entities.router, tags=["entities"])
router.include_router(matches.router, tags=["matches"])
router.include_router(votes.router, tags=["votes"])
router.include_router(settings.router, tags=["settings"])
router.include_router(providers.router, tags=["providers"])
router.include_router(download.router, tags=["download"])
router.include_router(lyrics.router, tags=["lyrics"])
router.include_router(reports.router, tags=["reports"])
router.include_router(admin.router, tags=["admin"])
