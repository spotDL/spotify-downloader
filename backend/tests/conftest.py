"""Pytest configuration and fixtures."""

from __future__ import annotations

import os
from pathlib import Path
import uuid
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from spotdl.core.security import create_access_token
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.db.database import get_db_session
from spotdl.db.models.base import Base
from spotdl.db.models.match import Match as MatchModel, MatchType
from spotdl.db.models.user import User
from spotdl.db.models.vote import Vote, VoteType
from spotdl.main import app

# Use SQLite for tests by default, PostgreSQL for CI
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)

# VCR configuration for cassette recording
CASSETTES_DIR = Path(__file__).parent / "cassettes"


def _scrub_response_headers(response: dict) -> dict:
    """Remove sensitive headers from VCR responses before recording."""
    headers_to_remove = ["set-cookie", "x-request-id"]
    if "headers" in response:
        response["headers"] = {
            k: v
            for k, v in response["headers"].items()
            if k.lower() not in headers_to_remove
        }
    return response


@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration for recording HTTP interactions.

    Uses 'once' mode which records cassettes if they don't exist,
    otherwise plays them back. Set VCR_RECORD_MODE=new_episodes
    to update existing cassettes.
    """
    record_mode = os.environ.get("VCR_RECORD_MODE", "once")
    return {
        "cassette_library_dir": str(CASSETTES_DIR),
        "record_mode": record_mode,
        "match_on": ["uri", "method"],
        "filter_headers": [
            "authorization",
            "cookie",
            "x-api-key",
            "user-agent",
        ],
        "filter_query_parameters": [
            "client_id",
            "client_secret",
        ],
        "decode_compressed_response": True,
        "before_record_response": _scrub_response_headers,
    }


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database session override."""

    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password_here",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(test_user: User) -> str:
    """Create an auth token for the test user."""
    return create_access_token(str(test_user.id))


@pytest_asyncio.fixture
async def authenticated_client(
    db_session: AsyncSession, auth_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated async test client."""

    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_match(db_session: AsyncSession, test_user: User) -> MatchModel:
    """Create a test match."""
    match = MatchModel(
        source_platform="spotify",
        source_url="https://open.spotify.com/track/test123",
        target_platform="youtube",
        target_url="https://www.youtube.com/watch?v=xyz789",
        match_type=MatchType.SYSTEM,
        match_score=85.0,
    )
    db_session.add(match)
    await db_session.commit()
    await db_session.refresh(match)
    return match


@pytest.fixture
def sample_song() -> Song:
    """Create a sample song for testing."""
    return Song(
        name="Test Song",
        artists=["Artist One", "Artist Two"],
        artist="Artist One",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="test123",
        url="https://open.spotify.com/track/test123",
        album_name="Test Album",
        album_artist="Artist One",
        year=2024,
        isrc="USRC12345678",
        explicit=False,
    )


@pytest.fixture
def sample_result() -> Result:
    """Create a sample result for testing."""
    return Result(
        platform=TargetPlatform.YOUTUBE_MUSIC,
        url="https://music.youtube.com/watch?v=abc123",
        verified=True,
        name="Artist One - Test Song",
        duration=181,
        artist="Artist One",
        platform_id="abc123",
        artists=("Artist One", "Artist Two"),
        album_name="Test Album",
    )


@pytest.fixture
def sample_result_unverified() -> Result:
    """Create an unverified result for testing."""
    return Result(
        platform=TargetPlatform.YOUTUBE,
        url="https://www.youtube.com/watch?v=xyz789",
        verified=False,
        name="Test Song - Artist One",
        duration=185,
        artist="RandomChannel",
        platform_id="xyz789",
        artists=("RandomChannel",),
    )


def create_song(
    name: str = "Test Song",
    artists: list[str] | None = None,
    duration: int = 180,
    album_name: str = "Test Album",
    explicit: bool = False,
    **kwargs: Any,
) -> Song:
    """Helper to create songs with default values."""
    if artists is None:
        artists = ["Artist One"]

    return Song(
        name=name,
        artists=artists,
        artist=artists[0] if artists else "",
        duration=duration,
        platform=Platform.SPOTIFY,
        platform_id=str(uuid.uuid4())[:8],
        url=f"https://open.spotify.com/track/{uuid.uuid4()}",
        album_name=album_name,
        album_artist=artists[0] if artists else "",
        explicit=explicit,
        **kwargs,
    )


def create_result(
    name: str = "Test Song",
    duration: int = 180,
    verified: bool = True,
    artists: tuple[str, ...] | None = None,
    platform: TargetPlatform = TargetPlatform.YOUTUBE_MUSIC,
    album_name: str | None = None,
    explicit: bool = False,
    isrc_search: bool = False,
    **kwargs: Any,
) -> Result:
    """Helper to create results with default values."""
    platform_id = str(uuid.uuid4())[:11]
    # Use default if None, but allow empty tuple
    if artists is None:
        artists = ("Unknown",)
    # Get artist from artists tuple, defaulting to "Unknown" if empty
    artist = artists[0] if artists else "Unknown"
    return Result(
        platform=platform,
        url=f"https://music.youtube.com/watch?v={platform_id}",
        verified=verified,
        name=name,
        duration=duration,
        artist=artist,
        platform_id=platform_id,
        artists=artists if artists else (),
        album_name=album_name,
        explicit=explicit,
        isrc_search=isrc_search,
        **kwargs,
    )
