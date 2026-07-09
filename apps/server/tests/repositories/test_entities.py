"""Offline (in-memory SQLite) tests for the canonical entity repositories."""

import pytest
from spotdl_server.db.models import Artist
from spotdl_server.repositories.entities import (
    AlbumRepository,
    ArtistRepository,
    PlaylistRepository,
    TrackRepository,
    normalize_artist_name,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def test_track_create_get_with_relations(session: AsyncSession) -> None:
    albums = AlbumRepository(session)
    artists = ArtistRepository(session)
    tracks = TrackRepository(session)

    album = await albums.create(name="Abbey Road", year=1969)
    artist, _ = await artists.get_or_create_by_normalized_name("The Beatles")
    track = await tracks.create(name="Come Together", duration_ms=259000, album_id=album.id)
    await tracks.set_artists(track, [artist.id])

    fetched = await tracks.get(track.id)
    assert fetched is not None
    assert fetched.name == "Come Together"
    assert fetched.album is not None
    assert fetched.album.name == "Abbey Road"
    assert [a.name for a in fetched.artists] == ["The Beatles"]


async def test_update_mutates_fields(session: AsyncSession) -> None:
    tracks = TrackRepository(session)
    track = await tracks.create(name="Old", duration_ms=1000)
    updated = await tracks.update(track, name="New", year=2020)
    assert updated.name == "New"
    assert updated.year == 2020


async def test_ordered_m2m_round_trips_positions(session: AsyncSession) -> None:
    artists = ArtistRepository(session)
    tracks = TrackRepository(session)
    playlists = PlaylistRepository(session)

    a0, _ = await artists.get_or_create_by_normalized_name("Main")
    a1, _ = await artists.get_or_create_by_normalized_name("Feat One")
    a2, _ = await artists.get_or_create_by_normalized_name("Feat Two")

    track = await tracks.create(name="Song")
    await tracks.set_artists(track, [a0.id, a1.id, a2.id])

    fetched = await tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["Main", "Feat One", "Feat Two"]

    t1 = await tracks.create(name="T1")
    t2 = await tracks.create(name="T2")
    playlist = await playlists.create(name="My List")
    await playlists.set_tracks(playlist, [t2.id, t1.id])

    fetched_pl = await playlists.get(playlist.id)
    assert fetched_pl is not None
    assert [t.name for t in fetched_pl.tracks] == ["T2", "T1"]


async def test_get_or_create_by_isrc_idempotent(session: AsyncSession) -> None:
    tracks = TrackRepository(session)
    first, created_1 = await tracks.get_or_create_by_isrc("USABC1234567")
    second, created_2 = await tracks.get_or_create_by_isrc("USABC1234567")
    assert created_1 is True
    assert created_2 is False
    assert first.id == second.id


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  The  Beatles ", "the beatles"),
        ("The Beatles", "the beatles"),
        ("BØRNS", "børns"),
        ("ＡＢＣ", "abc"),  # NFKC full-width → ascii
        ("Sigur\tRós\n", "sigur rós"),
        ("", ""),
    ],
)
def test_normalize_artist_name(raw: str, expected: str) -> None:
    assert normalize_artist_name(raw) == expected


async def test_get_or_create_by_normalized_name_dedupes_case_and_whitespace(
    session: AsyncSession,
) -> None:
    artists = ArtistRepository(session)
    first, created_1 = await artists.get_or_create_by_normalized_name("The Beatles")
    second, created_2 = await artists.get_or_create_by_normalized_name("the  beatles")

    assert (created_1, created_2) == (True, False)
    assert first.id == second.id
    # Display name keeps the first casing; the normalized key is the dedup boundary.
    assert second.name == "The Beatles"
    assert second.normalized_name == "the beatles"

    count = await session.execute(select(func.count()).select_from(Artist))
    assert int(count.scalar_one()) == 1


async def test_set_artists_is_replace_and_rerunnable(session: AsyncSession) -> None:
    artists = ArtistRepository(session)
    tracks = TrackRepository(session)

    a0, _ = await artists.get_or_create_by_normalized_name("A")
    a1, _ = await artists.get_or_create_by_normalized_name("B")
    a2, _ = await artists.get_or_create_by_normalized_name("C")

    track = await tracks.create(name="Song")
    await tracks.set_artists(track, [a0.id, a1.id])

    fetched = await tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["A", "B"]

    # Full replace with a different ordered set — no orphans, deterministic order.
    await tracks.set_artists(track, [a2.id, a0.id])
    fetched = await tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["C", "A"]

    # Re-running with the same set is a no-op (idempotent).
    await tracks.set_artists(track, [a2.id, a0.id])
    fetched = await tracks.get(track.id)
    assert fetched is not None
    assert [a.name for a in fetched.artists] == ["C", "A"]
