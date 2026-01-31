"""API v1 endpoints."""

from fastapi import APIRouter

from spotdl.api.v1 import auth, health, matches, songs, votes

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, tags=["auth"])
router.include_router(songs.router, tags=["songs"])
router.include_router(matches.router, tags=["matches"])
router.include_router(votes.router, tags=["votes"])
