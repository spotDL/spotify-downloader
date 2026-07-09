"""Offline end-to-end integration smoke test for the whole download pipeline.

This is the one test that composes the *real* engine wiring
(:func:`build_default_engine`) with a **real ffmpeg** and **real mutagen**, while
staying fully offline: only the audio-fetch seam is monkeypatched to a fake that
hands back the committed synthetic-silence fixture ``fixtures/tiny.opus`` instead
of hitting yt-dlp / the network. Cover download and synced-lyrics search stay as
the real collaborators but are never exercised over the network (no cover URL is
set; the ``.lrc`` comes from synced lyrics carried on the request), and
SponsorBlock is disabled.

It proves plan -> fetch -> convert -> embed -> post actually composes through the
public helper Plan 7 will call:

- **opus** output exercises the move-not-reencode fast path (source container ==
  output container, bitrate ``disable``), then real mutagen embeds vorbis tags.
- **mp3** output exercises the ffmpeg re-encode path (opus -> mp3), then real
  mutagen writes ID3 frames.
- a synced :class:`Lyrics` on the request yields a ``.lrc`` sidecar.

Gated by ``requires_ffmpeg`` (autoskips when no ffmpeg binary is present; CI
installs one). The fixture is a few-KB generated-silence file — no real media.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from spotdl_core.download import (
    DownloadConfig,
    DownloadRequest,
    OutcomeStatus,
    OutputFormat,
    build_default_engine,
)
from spotdl_core.download.context import BITRATE_AUTO, BITRATE_DISABLE
from spotdl_core.download.fetch import FetchResult, YtDlpFetcher
from spotdl_core.model import AlbumRef, AudioCandidate, Lyrics, LyricsKind, ProviderId, Track

FIXTURES = Path(__file__).parent / "fixtures"
TINY_OPUS = FIXTURES / "tiny.opus"

TRACK_URL = "https://open.spotify.com/track/sp123"
SOURCE_URL = "https://music.youtube.com/watch?v=abc123"
SYNCED_LRC = "[00:01.00]First synced line\n[00:12.34]Second synced line"


def _install_fake_fetch(monkeypatch: pytest.MonkeyPatch, ext: str) -> None:
    """Monkeypatch ``YtDlpFetcher.fetch`` (the seam ``build_default_engine`` wires)
    to copy ``tiny.opus`` into the temp dir under ``.<ext>`` instead of fetching.

    Everything downstream — convert, embed, post — runs for real.
    """
    import shutil

    async def fake_fetch(
        self: YtDlpFetcher,
        candidate: AudioCandidate,
        *,
        output_format: OutputFormat,
        temp_dir: Path,
        on_progress: Any = None,
    ) -> FetchResult:
        temp_dir.mkdir(parents=True, exist_ok=True)
        dest = temp_dir / f"faketrack.{ext}"
        shutil.copy(TINY_OPUS, dest)
        return FetchResult(
            path=dest,
            ext=ext,
            source_url=candidate.url,
            abr=None,
            info={"id": "faketrack", "ext": ext},
        )

    monkeypatch.setattr(YtDlpFetcher, "fetch", fake_fetch)


def _track() -> Track:
    return Track(
        name="Test Song",
        artists=("Test Artist",),
        duration_ms=1_000,
        album=AlbumRef(name="Test Album", album_artist="Test Artist"),
        provider=ProviderId.SPOTIFY,
        provider_id="sp123",
    )


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YTMUSIC,
        provider_id="abc123",
        url=SOURCE_URL,
        name="Test Song",
    )


def _config(tmp_path: Path) -> DownloadConfig:
    return DownloadConfig(
        output_dir=tmp_path / "out",
        temp_dir=tmp_path / "tmp",
        ffmpeg_path="ffmpeg",
    )


def _request(**overrides: Any) -> DownloadRequest:
    base: dict[str, Any] = {
        "track": _track(),
        "candidate": _candidate(),
        "output_template": "",
        "track_url": TRACK_URL,
        "skip_album_art": True,  # no cover URL anyway; keeps the run offline
    }
    base.update(overrides)
    return DownloadRequest(**base)


async def test_end_to_end_opus_copy_path_embeds_tags_and_lrc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requires_ffmpeg: None
) -> None:
    """OPUS output + ``disable`` bitrate: source container matches output, so the
    move fast path relocates the file (no re-encode), then real mutagen embeds
    vorbis-comment tags and a ``.lrc`` is written from the synced request lyrics.
    """
    _install_fake_fetch(monkeypatch, ext="opus")
    config = _config(tmp_path)
    lyrics = Lyrics(kind=LyricsKind.SYNCED, text=SYNCED_LRC, source=ProviderId.LRCLIB)
    request = _request(
        output_format=OutputFormat.OPUS,
        bitrate=BITRATE_DISABLE,
        generate_lrc=True,
        lyrics=lyrics,
    )

    engine = build_default_engine(config)
    outcome = await engine.download(request)

    assert outcome.status is OutcomeStatus.DOWNLOADED
    assert outcome.path is not None
    assert outcome.path.exists()
    assert outcome.path.suffix == ".opus"

    # Real mutagen read-back: vorbis-comment title was embedded.
    from mutagen.oggopus import OggOpus

    audio = OggOpus(str(outcome.path))
    assert audio["title"] == ["Test Song"]

    # Synced lyrics on the request produced an .lrc sidecar.
    lrc_path = outcome.path.with_suffix(".lrc")
    assert lrc_path.exists()
    assert lrc_path.read_text(encoding="utf-8") == SYNCED_LRC

    # Fast path consumed the temp file (nothing left behind).
    assert list(config.temp_dir.glob("*.opus")) == []


async def test_end_to_end_mp3_reencode_embeds_id3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requires_ffmpeg: None
) -> None:
    """MP3 output from an opus source: containers differ, so ffmpeg re-encodes
    (libmp3lame), then real mutagen writes ID3 frames read back here.
    """
    _install_fake_fetch(monkeypatch, ext="opus")
    config = _config(tmp_path)
    request = _request(output_format=OutputFormat.MP3, bitrate=BITRATE_AUTO)

    engine = build_default_engine(config)
    outcome = await engine.download(request)

    assert outcome.status is OutcomeStatus.DOWNLOADED
    assert outcome.path is not None
    assert outcome.path.exists()
    assert outcome.path.suffix == ".mp3"

    from mutagen.id3 import ID3

    tags = ID3(str(outcome.path))
    assert tags.getall("TIT2")[0].text[0] == "Test Song"
