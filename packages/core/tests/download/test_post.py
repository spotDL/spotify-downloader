"""Tests for ``spotdl_core.download.post`` — post-processing utilities:
``.lrc`` generation, m3u playlist building (``{list}`` templating), archive
updates, and SponsorBlock chapter removal.

The lyrics-search and SponsorBlock external calls are reached only through
injectable seams, so the default suite is fully offline (no network, no
``syncedlyrics`` install, no yt-dlp postprocessors). The ``{list}`` templating
semantics and the ``SPONSOR_BLOCK_CATEGORIES`` set are a CONTRACT (v4 parity).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from spotdl_core.download.context import (
    DownloadContext,
    DownloadRequest,
    OutputFormat,
)
from spotdl_core.download.post import (
    SPONSOR_BLOCK_CATEGORIES,
    M3uEntry,
    SponsorBlockStep,
    SyncedLyricsLibrary,
    archive_update,
    create_m3u_content,
    gen_m3u_files,
    generate_lrc,
)
from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
    Lyrics,
    LyricsKind,
    ProviderId,
    Track,
)
from spotdl_core.providers.errors import PostProcessingFailed

SYNCED_LRC = "[00:01.00]First synced line\n[00:12.34]Second synced line\n[00:23.45]Third"
PLAIN_TEXT = "First plain line\nSecond plain line"
SOURCE_URL = "https://music.youtube.com/watch?v=abc123"


# --- helpers --------------------------------------------------------------


def _track(
    *,
    name: str = "Song One",
    artists: tuple[str, ...] = ("First Artist",),
    duration_ms: int = 200_000,
    album_artist: str = "Album Artist",
) -> Track:
    return Track(
        name=name,
        artists=artists,
        duration_ms=duration_ms,
        album=AlbumRef(name="Test Album", album_artist=album_artist),
        provider=ProviderId.SPOTIFY,
        provider_id="sp123",
    )


def _request(
    *,
    track: Track | None = None,
    lyrics: Lyrics | None = None,
    output_format: OutputFormat = OutputFormat.MP3,
) -> DownloadRequest:
    return DownloadRequest(
        track=track if track is not None else _track(),
        candidate=AudioCandidate(
            provider=ProviderId.YTMUSIC,
            provider_id="abc123",
            url=SOURCE_URL,
            name="Song One",
        ),
        output_template="",
        output_format=output_format,
        lyrics=lyrics,
    )


def _context(final_path: Path, *, source_info: dict | None = None) -> DownloadContext:
    return DownloadContext(
        request=_request(),
        output_path=final_path,
        final_path=final_path,
        source_info=source_info if source_info is not None else {"id": "abc123"},
    )


# --- offline seams --------------------------------------------------------


class FakeSyncedLyricsSearch:
    """Offline ``SyncedLyricsSearch`` recording every query."""

    def __init__(self, result: str | None = None) -> None:
        self._result = result
        self.queries: list[str] = []

    def search(self, query: str) -> str | None:
        self.queries.append(query)
        return self._result


class FakeSponsorBlock:
    """Offline ``SponsorBlock``: returns a chosen path or raises a chosen error."""

    def __init__(self, result: Path | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls: list[tuple[dict, Path]] = []

    def process(self, info: dict, audio_path: Path) -> Path:
        self.calls.append((info, audio_path))
        if self._error is not None:
            raise self._error
        return self._result if self._result is not None else audio_path


# --- lrc ------------------------------------------------------------------


def test_generate_lrc_prefers_synced_request_lyrics(tmp_path: Path) -> None:
    output = tmp_path / "Song One.mp3"
    lyrics = Lyrics(kind=LyricsKind.SYNCED, text=SYNCED_LRC, source=ProviderId.LRCLIB)
    search = FakeSyncedLyricsSearch(result="should-not-be-used")

    result = generate_lrc(_request(lyrics=lyrics), output, search)

    assert result == tmp_path / "Song One.lrc"
    assert result.read_text(encoding="utf-8") == SYNCED_LRC
    # Request already carried synced lyrics -> the search seam is never touched.
    assert search.queries == []


def test_generate_lrc_no_file_when_plain_lyrics_and_search_empty(tmp_path: Path) -> None:
    output = tmp_path / "Song One.mp3"
    lyrics = Lyrics(kind=LyricsKind.PLAIN, text=PLAIN_TEXT, source=ProviderId.GENIUS)
    search = FakeSyncedLyricsSearch(result=None)

    result = generate_lrc(_request(lyrics=lyrics), output, search)

    assert result is None
    assert not (tmp_path / "Song One.lrc").exists()
    # Plain (non-synced) request lyrics -> fall through to the injected search.
    assert search.queries == ["First Artist - Song One"]


def test_generate_lrc_uses_search_result_when_no_request_lyrics(tmp_path: Path) -> None:
    output = tmp_path / "Song One.mp3"
    search = FakeSyncedLyricsSearch(result=SYNCED_LRC)

    result = generate_lrc(_request(lyrics=None), output, search)

    assert result == tmp_path / "Song One.lrc"
    assert result.read_text(encoding="utf-8") == SYNCED_LRC
    assert search.queries == ["First Artist - Song One"]


def test_generate_lrc_swallows_search_failure(tmp_path: Path) -> None:
    class BoomSearch:
        def search(self, query: str) -> str | None:
            raise RuntimeError("network down")

    output = tmp_path / "Song One.mp3"
    result = generate_lrc(_request(lyrics=None), output, BoomSearch())

    assert result is None
    assert not (tmp_path / "Song One.lrc").exists()


def test_synced_lyrics_library_returns_none_without_extra() -> None:
    # ``syncedlyrics`` is an optional extra and is not installed in the default
    # suite; the library seam must degrade to None rather than raising.
    assert SyncedLyricsLibrary().search("anything") is None


# --- m3u content (pure) ---------------------------------------------------


def test_create_m3u_content_header_extinf_and_rendered_path(tmp_path: Path) -> None:
    entries = [
        M3uEntry(track=_track(name="Song One"), path=tmp_path / "a.mp3", list_name=None),
        M3uEntry(track=_track(name="Song Two"), path=tmp_path / "b.mp3", list_name=None),
    ]

    content = create_m3u_content(entries, "{artists} - {title}", OutputFormat.MP3)
    lines = content.splitlines()

    assert lines[0] == "#EXTM3U"
    assert lines[1] == "#EXTINF:200,Album Artist - Song One"
    assert lines[2] == "First Artist - Song One.mp3"
    assert lines[3] == "#EXTINF:200,Album Artist - Song Two"
    assert lines[4] == "First Artist - Song Two.mp3"
    # Rendered paths are relative (no absolute output dir baked in).
    assert not Path(lines[2]).is_absolute()


def test_create_m3u_content_detect_formats_picks_existing_variant(tmp_path: Path) -> None:
    audio = tmp_path / "song.mp3"
    (tmp_path / "song.opus").write_bytes(b"synthetic")  # the existing variant
    entry = M3uEntry(track=_track(name="Song One"), path=audio, list_name=None)

    content = create_m3u_content(
        [entry],
        "{artists} - {title}",
        OutputFormat.MP3,
        detect_formats=(OutputFormat.OPUS,),
    )

    # The existing .opus variant wins over the default mp3 extension.
    assert content.splitlines()[2] == "First Artist - Song One.opus"


def test_create_m3u_content_detect_formats_falls_back_to_output_format(tmp_path: Path) -> None:
    entry = M3uEntry(track=_track(name="Song One"), path=tmp_path / "song.mp3", list_name=None)

    content = create_m3u_content(
        [entry],
        "{artists} - {title}",
        OutputFormat.MP3,
        detect_formats=(OutputFormat.OPUS,),  # no .opus file exists
    )

    assert content.splitlines()[2] == "First Artist - Song One.mp3"


# --- m3u files (I/O) ------------------------------------------------------


def _list_entries(base: Path) -> list[M3uEntry]:
    return [
        M3uEntry(track=_track(name="A"), path=base / "A.mp3", list_name="Playlist One"),
        M3uEntry(track=_track(name="B"), path=base / "B.mp3", list_name="Playlist One"),
        M3uEntry(track=_track(name="C"), path=base / "C.mp3", list_name="Playlist Two"),
    ]


def test_gen_m3u_files_default_filename_single_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    written = gen_m3u_files(_list_entries(tmp_path), None, "{artists} - {title}", OutputFormat.MP3)

    assert len(written) == 1
    assert written[0].name == "Playlist One.m3u8"
    assert written[0].exists()


def test_gen_m3u_files_list_token_one_file_per_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    written = gen_m3u_files(
        _list_entries(tmp_path), "{list}.m3u8", "{artists} - {title}", OutputFormat.MP3
    )

    names = sorted(path.name for path in written)
    assert names == ["Playlist One.m3u8", "Playlist Two.m3u8"]
    # The per-list file only contains that list's tracks.
    one = next(p for p in written if p.name == "Playlist One.m3u8").read_text(encoding="utf-8")
    assert "First Artist - A.mp3" in one
    assert "First Artist - C.mp3" not in one


def test_gen_m3u_files_indexed_token_single_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    written = gen_m3u_files(
        _list_entries(tmp_path), "{list[0]}.m3u8", "{artists} - {title}", OutputFormat.MP3
    )

    assert len(written) == 1
    assert written[0].name == "Playlist One.m3u8"
    # The single indexed file spans every track, across both lists.
    content = written[0].read_text(encoding="utf-8")
    assert "First Artist - A.mp3" in content
    assert "First Artist - C.mp3" in content


def test_gen_m3u_files_plain_filename_used_verbatim(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    written = gen_m3u_files(
        _list_entries(tmp_path), "everything", "{artists} - {title}", OutputFormat.MP3
    )

    assert len(written) == 1
    assert written[0].name == "everything.m3u8"  # .m3u8 appended when missing


def test_gen_m3u_files_list_name_without_lists_warns_and_writes_nothing(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    monkeypatch.chdir(tmp_path)
    entries = [M3uEntry(track=_track(name="A"), path=tmp_path / "A.mp3", list_name=None)]

    with caplog.at_level(logging.WARNING):
        written = gen_m3u_files(entries, "{list}.m3u8", "{artists} - {title}", OutputFormat.MP3)

    assert written == []
    assert list(tmp_path.glob("*.m3u8")) == []
    assert any("list" in record.message.lower() for record in caplog.records)


# --- archive --------------------------------------------------------------


def test_archive_update_adds_only_successes_by_default() -> None:
    current = frozenset({"https://existing/1"})
    results = [
        ("https://ok/2", True),
        ("https://failed/3", False),
    ]

    updated = archive_update(current, results, add_unavailable=False)

    assert updated == frozenset({"https://existing/1", "https://ok/2"})


def test_archive_update_adds_unavailable_when_requested() -> None:
    results = [
        ("https://ok/1", True),
        ("https://failed/2", False),
    ]

    updated = archive_update(frozenset(), results, add_unavailable=True)

    assert updated == frozenset({"https://ok/1", "https://failed/2"})


def test_sponsor_block_categories_are_the_eight_v4_keys() -> None:
    assert set(SPONSOR_BLOCK_CATEGORIES) == {
        "sponsor",
        "intro",
        "outro",
        "selfpromo",
        "preview",
        "filler",
        "interaction",
        "music_offtopic",
    }


# --- sponsorblock ---------------------------------------------------------


async def test_sponsor_block_step_swaps_final_path(tmp_path: Path) -> None:
    original = tmp_path / "song.mp3"
    original.write_bytes(b"synthetic")
    modified = tmp_path / "song.cut.mp3"
    modified.write_bytes(b"synthetic-cut")
    sponsor = FakeSponsorBlock(result=modified)

    result = await SponsorBlockStep(sponsor)(_context(original))

    assert result.final_path == modified
    assert sponsor.calls[0][1] == original


async def test_sponsor_block_step_degrades_when_postprocessors_unavailable(tmp_path: Path) -> None:
    original = tmp_path / "song.mp3"
    original.write_bytes(b"synthetic")
    sponsor = FakeSponsorBlock(error=ImportError("no ModifyChaptersPP"))

    result = await SponsorBlockStep(sponsor)(_context(original))

    # Missing yt-dlp postprocessors must not fail the download; final_path is kept.
    assert result.final_path == original


async def test_sponsor_block_step_wraps_genuine_error(tmp_path: Path) -> None:
    original = tmp_path / "song.mp3"
    original.write_bytes(b"synthetic")
    sponsor = FakeSponsorBlock(error=RuntimeError("sponsorblock api 500"))

    with pytest.raises(PostProcessingFailed) as excinfo:
        await SponsorBlockStep(sponsor)(_context(original))

    assert excinfo.value.step == "post"
