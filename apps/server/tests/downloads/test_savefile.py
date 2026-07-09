"""Task 2 — ``.spotdl`` v2 save-file model + deterministic dump (CONTRACT 7)."""

from __future__ import annotations

from spotdl_server.downloads.savefile import (
    SAVE_FILE_VERSION,
    SaveFileDownload,
    SaveFileMatch,
    SaveFileSong,
    SaveFileV2,
    dump_save_file,
)


def _song(**overrides: object) -> SaveFileSong:
    base = dict(
        name="Song",
        artists=["A", "B"],
        duration_ms=210_000,
        download=SaveFileDownload(
            output_format="mp3",
            bitrate="auto",
            output_template="{artists} - {title}.{output-ext}",
            status="completed",
        ),
    )
    base.update(overrides)
    return SaveFileSong(**base)  # type: ignore[arg-type]


def test_save_file_version_constant() -> None:
    assert SAVE_FILE_VERSION == 2
    assert SaveFileV2(kind="single", created_at="2026-01-01T00:00:00Z", songs=[]).version == 2


def test_song_with_only_required_fields_validates() -> None:
    song = _song()
    assert song.artist is None
    assert song.genres == []
    assert song.match is None
    assert song.isrc is None
    assert song.list_position is None


def test_song_with_match() -> None:
    song = _song(
        match=SaveFileMatch(provider="youtube", provider_id="abc", url="https://y/abc"),
    )
    assert song.match is not None
    assert song.match.verified is False
    assert song.match.artists == []


def test_save_file_roundtrip() -> None:
    model = SaveFileV2(
        kind="playlist",
        name="My Playlist",
        source="https://open.spotify.com/playlist/x",
        created_at="2026-01-01T00:00:00Z",
        matcher_version="v5",
        songs=[_song(), _song(name="Two")],
    )
    again = SaveFileV2.model_validate_json(model.model_dump_json())
    assert again == model


def test_dump_is_deterministic_and_reparses() -> None:
    model = SaveFileV2(
        kind="album",
        name="Album",
        created_at="2026-01-01T00:00:00Z",
        songs=[_song()],
    )
    text = dump_save_file(model)
    # stable indent + trailing newline
    assert text.endswith("\n")
    assert '  "version": 2' in text
    assert text == dump_save_file(model)  # deterministic across calls
    reparsed = SaveFileV2.model_validate_json(text)
    assert reparsed == model


# ------------------------------------------------------------ provenance
class _Snap:
    """Bare snapshot stand-in: provider (StrEnum-like) + provider_entity_id."""

    def __init__(self, provider: object, provider_entity_id: str) -> None:
        self.provider = provider
        self.provider_entity_id = provider_entity_id


def test_pick_track_provenance_prefers_priority_order() -> None:
    from spotdl_core.model import ProviderId
    from spotdl_server.downloads.savefile import pick_track_provenance
    from spotdl_server.repositories.merge import SOURCE_PRIORITY

    snaps = [
        _Snap(ProviderId.MUSICBRAINZ, "mb-1"),
        _Snap(ProviderId.SPOTIFY, "sp-1"),
        _Snap(ProviderId.DEEZER, "dz-1"),
    ]
    picked = pick_track_provenance(snaps, SOURCE_PRIORITY)
    assert picked is not None
    assert picked.provider == "spotify"
    assert picked.provider_id == "sp-1"
    assert picked.track_url == "https://open.spotify.com/track/sp-1"


def test_pick_track_provenance_unknown_provider_has_no_url() -> None:
    from spotdl_server.downloads.savefile import pick_track_provenance

    picked = pick_track_provenance([_Snap("bandcamp", "bc-9")], [])
    assert picked is not None
    assert picked.provider == "bandcamp"
    assert picked.track_url is None


def test_pick_track_provenance_empty() -> None:
    from spotdl_server.downloads.savefile import pick_track_provenance

    assert pick_track_provenance([], []) is None


def test_build_save_file_fills_provenance_fields() -> None:
    from types import SimpleNamespace
    from uuid import uuid4

    from spotdl_server.downloads.savefile import TrackProvenance, build_save_file

    track_id = uuid4()
    job = SimpleNamespace(
        track_id=track_id,
        match_id=None,
        output_format="mp3",
        bitrate="auto",
        output_template="{artists} - {title}.{output-ext}",
        output_path=None,
        status="completed",
        skip_reason=None,
        error_step=None,
        list_position=1,
    )
    batch = SimpleNamespace(kind="single", name=None, source="q", created_at=None, total_jobs=1)
    track = SimpleNamespace(
        artists=[SimpleNamespace(name="A")],
        name="Song",
        duration_ms=1000,
        album=None,
        isrc=None,
        explicit=None,
        track_number=None,
        disc_number=None,
        year=None,
        genres=[],
        popularity=None,
    )
    provenance = {
        track_id: TrackProvenance(
            provider="spotify",
            provider_id="sp-42",
            track_url="https://open.spotify.com/track/sp-42",
        )
    }
    model = build_save_file(batch, [job], {track_id: track}, {}, provenance)
    song = model.songs[0]
    assert song.provider == "spotify"
    assert song.provider_id == "sp-42"
    assert song.track_url == "https://open.spotify.com/track/sp-42"

    # without provenance the same inputs keep the fields null
    bare = build_save_file(batch, [job], {track_id: track}, {})
    assert bare.songs[0].provider_id is None
    assert bare.songs[0].track_url is None
