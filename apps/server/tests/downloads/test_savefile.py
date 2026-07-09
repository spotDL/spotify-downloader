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
