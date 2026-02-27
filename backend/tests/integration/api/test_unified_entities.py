"""Integration tests for unified entity-first API endpoints."""
# ruff: noqa: TC002

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from spotdl.core.services.match import Match
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song

pytestmark = pytest.mark.asyncio


@pytest.fixture
def source_song() -> Song:
    return Song(
        name="Test Song",
        artists=["Artist 1"],
        artist="Artist 1",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="sp_test_song",
        url="https://open.spotify.com/track/sp_test_song",
        album_name="Test Album",
        album_id="sp_test_album",
        year=2024,
    )


@pytest.fixture
def target_result() -> Result:
    return Result(
        name="Test Song (Official)",
        artists=["Artist 1"],
        artist="Artist 1",
        duration=201,
        platform=TargetPlatform.YOUTUBE_MUSIC,
        platform_id="ytm_test_song",
        url="https://music.youtube.com/watch?v=ytm_test_song",
        album_name="Test Album",
        cover_url="https://i.ytimg.com/vi/test/hqdefault.jpg",
        views=12345,
        verified=True,
    )


def _mock_song_service(source_song: Song) -> MagicMock:
    service = MagicMock()
    service.supported_platforms = [Platform.SPOTIFY]
    service.search = AsyncMock(return_value=[source_song])
    service.get_track = AsyncMock(return_value=source_song)
    service.get_album = AsyncMock()
    service.get_artist = AsyncMock()
    service.get_playlist = AsyncMock()
    return service


async def test_discover_entities_from_query(
    client: AsyncClient,
    source_song: Song,
) -> None:
    with patch("spotdl.core.services.entity_unified.get_song_service") as get_song_service_mock:
        get_song_service_mock.return_value = _mock_song_service(source_song)

        response = await client.post(
            "/api/v1/entities/discover",
            json={"query": "Artist 1 - Test Song", "types": ["track"], "limit": 10},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(entity["type"] == "track" for entity in payload["entities"])
    assert payload["query_type"] == "text"


async def test_relations_discover_and_vote_lifecycle(
    authenticated_client: AsyncClient,
    source_song: Song,
    target_result: Result,
) -> None:
    relation_id: str

    with (
        patch("spotdl.core.services.entity_unified.get_song_service") as get_song_service_mock,
        patch("spotdl.core.services.entity_unified.get_match_service") as get_match_service_mock,
    ):
        get_song_service_mock.return_value = _mock_song_service(source_song)

        match_service = MagicMock()
        match_service.find_matches = AsyncMock(
            return_value=[
                Match(
                    source_song=source_song,
                    target_result=target_result,
                    score=89.0,
                    confidence=0.89,
                )
            ]
        )
        get_match_service_mock.return_value = match_service

        discover_response = await authenticated_client.post(
            "/api/v1/entities/discover",
            json={"query": "Artist 1 - Test Song", "types": ["track"], "limit": 10},
        )
        assert discover_response.status_code == 200
        discovered = discover_response.json()
        source_entity = next(
            entity for entity in discovered["entities"] if entity["type"] == "track"
        )

        relations_response = await authenticated_client.post(
            f"/api/v1/entities/{source_entity['id']}/relations:discover",
            json={"target_providers": ["youtube_music"], "limit": 5},
        )
        assert relations_response.status_code == 200
        relations_payload = relations_response.json()
        assert relations_payload["total"] >= 1
        relation_id = relations_payload["relations"][0]["id"]

    upvote = await authenticated_client.post(
        f"/api/v1/relations/{relation_id}/vote",
        json={"vote": "up"},
    )
    assert upvote.status_code == 200
    upvote_payload = upvote.json()
    assert upvote_payload["upvotes"] == 1
    assert upvote_payload["user_vote"] == "up"

    remove_vote = await authenticated_client.post(
        f"/api/v1/relations/{relation_id}/vote",
        json={"vote": "remove"},
    )
    assert remove_vote.status_code == 200
    remove_payload = remove_vote.json()
    assert remove_payload["upvotes"] == 0
    assert remove_payload["user_vote"] is None


async def test_discover_open_graph_fallback(
    client: AsyncClient,
) -> None:
    with (
        patch("spotdl.core.services.entity_unified.get_song_service") as get_song_service_mock,
        patch(
            "spotdl.core.services.entity_unified._fetch_open_graph", new_callable=AsyncMock
        ) as fetch_og_mock,
    ):
        song_service = MagicMock()
        song_service.supported_platforms = []
        song_service.search = AsyncMock(return_value=[])
        song_service.get_track = AsyncMock()
        get_song_service_mock.return_value = song_service
        fetch_og_mock.return_value = {
            "name": "Example Article",
            "artist": "Example.com",
            "artists": ["Example.com"],
            "cover_url": "https://example.com/cover.jpg",
            "description": "Example description",
            "url": "https://example.com/path",
            "site_name": "Example.com",
        }

        response = await client.post(
            "/api/v1/entities/discover",
            json={"url": "https://example.com/path"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["entities"][0]["canonical"]["platform"] == "open_graph"
