"""Offline (in-memory SQLite) tests for EntityService — the read side.

EntityService maps already-persisted canonical ORM rows to service DTOs with
their relations (album, artists, ordered playlist tracks, matches, lyrics). It is
read-only: it never touches a provider. Missing entities raise the server-side
``NotFoundError`` (carrying the canonical ``entity_type`` + requested id), never
core's provider-facing ``EntityNotFound``. ``get_matches`` / ``get_lyrics`` return
an empty tuple for an existing-but-unmatched/unlyric'd track.

Each test calls ``session.expire_all()`` after seeding and before reading, so the
service exercises the real ``session.get`` + ``selectin`` eager-load path a fresh
per-request session would take (rather than reading warm identity-map objects).
"""

from __future__ import annotations

import uuid

import pytest
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId
from spotdl_server.db.models import Lyrics as LyricsModel
from spotdl_server.db.models import Match as MatchModel
from spotdl_server.repositories.entities import (
    AlbumRepository,
    ArtistRepository,
    PlaylistRepository,
    TrackRepository,
)
from spotdl_server.services.dto import (
    AlbumView,
    ArtistView,
    LyricsView,
    MatchView,
    PlaylistView,
    TrackView,
)
from spotdl_server.services.entities import EntityService
from spotdl_server.services.errors import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_track_with_relations(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Persist an album, an artist, and a track wired to both.

    Returns ``(track_id, album_id, artist_id)`` as plain UUIDs (safe to use after
    ``expire_all``).
    """
    albums = AlbumRepository(session)
    artists = ArtistRepository(session)
    tracks = TrackRepository(session)

    album = await albums.create(name="Greatest Hits", album_artist="Adele", year=2020)
    artist, _ = await artists.get_or_create_by_normalized_name("Adele")
    track = await tracks.create(
        name="Hello",
        duration_ms=295_000,
        isrc="USABC1234567",
        album_id=album.id,
        genres=["pop"],
    )
    await tracks.set_artists(track, [artist.id])
    await session.flush()
    return track.id, album.id, artist.id


async def _add_match(session: AsyncSession, track_id: uuid.UUID) -> None:
    session.add(
        MatchModel(
            track_id=track_id,
            target_provider=ProviderId.YOUTUBE,
            target_id="yt1",
            target_url="https://audio/yt1",
            score=0.91,
            matcher_version="v5.0",
            status=MatchStatus.AUTO,
            candidate_name="Hello",
            candidate_artists=["Adele"],
            candidate_duration_ms=295_000,
        )
    )
    await session.flush()


async def _add_lyrics(session: AsyncSession, track_id: uuid.UUID) -> None:
    session.add(
        LyricsModel(
            track_id=track_id,
            source=ProviderId.LRCLIB,
            kind=LyricsKind.PLAIN,
            text="Hello, it's me",
        )
    )
    await session.flush()


async def test_get_track_returns_view_with_relations(session: AsyncSession) -> None:
    track_id, album_id, _ = await _make_track_with_relations(session)
    await _add_match(session, track_id)
    await _add_lyrics(session, track_id)
    session.expire_all()
    service = EntityService(session=session)

    view = await service.get_track(track_id)

    assert isinstance(view, TrackView)
    assert view.id == str(track_id)
    assert view.name == "Hello"
    assert view.artists == ("Adele",)
    assert view.genres == ("pop",)
    assert view.album is not None
    assert view.album.id == str(album_id)
    assert view.album.name == "Greatest Hits"
    assert view.album.tracks == ()  # album is metadata-only when nested in a track
    assert len(view.matches) == 1
    assert view.matches[0].target_provider == ProviderId.YOUTUBE.value
    assert len(view.lyrics) == 1
    assert view.lyrics[0].source == ProviderId.LRCLIB.value


async def test_get_track_missing_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)
    missing = uuid.uuid4()

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_track(missing)

    assert excinfo.value.entity_type is EntityType.TRACK
    assert excinfo.value.entity_id == missing


async def test_get_track_invalid_id_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_track("not-a-uuid")

    assert excinfo.value.entity_type is EntityType.TRACK


async def test_get_album_returns_view_with_tracks(session: AsyncSession) -> None:
    _, album_id, _ = await _make_track_with_relations(session)
    session.expire_all()
    service = EntityService(session=session)

    view = await service.get_album(album_id)

    assert isinstance(view, AlbumView)
    assert view.id == str(album_id)
    assert view.name == "Greatest Hits"
    assert {t.name for t in view.tracks} == {"Hello"}
    # Nested listing tracks carry their artists but no album back-reference.
    assert view.tracks[0].artists == ("Adele",)
    assert view.tracks[0].album is None


async def test_get_album_missing_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)
    missing = uuid.uuid4()

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_album(missing)

    assert excinfo.value.entity_type is EntityType.ALBUM
    assert excinfo.value.entity_id == missing


async def test_get_artist_returns_view_with_tracks(session: AsyncSession) -> None:
    _, _, artist_id = await _make_track_with_relations(session)
    session.expire_all()
    service = EntityService(session=session)

    view = await service.get_artist(artist_id)

    assert isinstance(view, ArtistView)
    assert view.name == "Adele"
    assert {t.name for t in view.tracks} == {"Hello"}


async def test_get_artist_missing_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)
    missing = uuid.uuid4()

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_artist(missing)

    assert excinfo.value.entity_type is EntityType.ARTIST


async def test_get_playlist_returns_view_with_ordered_tracks(session: AsyncSession) -> None:
    tracks = TrackRepository(session)
    playlists = PlaylistRepository(session)
    t1 = await tracks.create(name="First", duration_ms=100_000)
    t2 = await tracks.create(name="Second", duration_ms=100_000)
    playlist = await playlists.create(name="My Mix", owner="me")
    await playlists.set_tracks(playlist, [t2.id, t1.id])  # explicit order t2, t1
    await session.flush()
    playlist_id = playlist.id
    session.expire_all()
    service = EntityService(session=session)

    view = await service.get_playlist(playlist_id)

    assert isinstance(view, PlaylistView)
    assert view.name == "My Mix"
    assert [t.name for t in view.tracks] == ["Second", "First"]  # order preserved


async def test_get_playlist_missing_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)
    missing = uuid.uuid4()

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_playlist(missing)

    assert excinfo.value.entity_type is EntityType.PLAYLIST


async def test_get_matches_returns_tuple(session: AsyncSession) -> None:
    track_id, _, _ = await _make_track_with_relations(session)
    await _add_match(session, track_id)
    session.expire_all()
    service = EntityService(session=session)

    matches = await service.get_matches(track_id)

    assert isinstance(matches, tuple)
    assert len(matches) == 1
    assert isinstance(matches[0], MatchView)
    assert matches[0].target_id == "yt1"


async def test_get_matches_on_unmatched_track_is_empty_tuple(session: AsyncSession) -> None:
    track_id, _, _ = await _make_track_with_relations(session)
    session.expire_all()
    service = EntityService(session=session)

    matches = await service.get_matches(track_id)

    assert matches == ()


async def test_get_matches_missing_track_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)
    missing = uuid.uuid4()

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_matches(missing)

    assert excinfo.value.entity_type is EntityType.TRACK
    assert excinfo.value.entity_id == missing


async def test_get_lyrics_returns_tuple(session: AsyncSession) -> None:
    track_id, _, _ = await _make_track_with_relations(session)
    await _add_lyrics(session, track_id)
    session.expire_all()
    service = EntityService(session=session)

    lyrics = await service.get_lyrics(track_id)

    assert isinstance(lyrics, tuple)
    assert len(lyrics) == 1
    assert isinstance(lyrics[0], LyricsView)
    assert lyrics[0].text == "Hello, it's me"


async def test_get_lyrics_on_unlyriced_track_is_empty_tuple(session: AsyncSession) -> None:
    track_id, _, _ = await _make_track_with_relations(session)
    session.expire_all()
    service = EntityService(session=session)

    lyrics = await service.get_lyrics(track_id)

    assert lyrics == ()


async def test_get_lyrics_missing_track_raises_not_found(session: AsyncSession) -> None:
    service = EntityService(session=session)
    missing = uuid.uuid4()

    with pytest.raises(NotFoundError) as excinfo:
        await service.get_lyrics(missing)

    assert excinfo.value.entity_type is EntityType.TRACK
