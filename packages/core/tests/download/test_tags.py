"""Tests for ``spotdl_core.download.tags`` — mutagen metadata embedding across
all six output containers (mp3/m4a/flac/ogg/opus/wav).

The per-container tag-preset tables are a CONTRACT (metadata parity: other tools
read these frames/atoms/keys). These tests embed a fully-populated ``Track`` into
a real, tiny synthetic-silence file (via the ``silent_audio`` session fixture,
which is ``requires_ffmpeg``-guarded) and re-open it with real mutagen to assert
each logical field lands in the right frame/atom/key. Cover fetching goes through
an injected offline ``CoverDownloader`` seam, so the default suite never touches
the network.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from spotdl_core.download.context import (
    DownloadRequest,
    OutputFormat,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.download.tags import (
    LRC_REGEX,
    M4A_TAG_PRESET,
    MP3_TAG_PRESET,
    CoverDownloader,
    EmbedStep,
    HttpCoverDownloader,
    embed_metadata,
)
from spotdl_core.model import (
    AlbumRef,
    AudioCandidate,
    Lyrics,
    LyricsKind,
    ProviderId,
    Track,
)
from spotdl_core.providers.errors import MetadataEmbedFailed

# --- synthetic constants --------------------------------------------------

# A clearly-synthetic byte blob with a JPEG SOI/EOI framing. mutagen stores the
# bytes verbatim; the content need not be a decodable image for tag round-trip.
FAKE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"synthetic-cover-data" * 4 + b"\xff\xd9"

TRACK_URL = "https://open.spotify.com/track/sp123"
SOURCE_URL = "https://music.youtube.com/watch?v=abc123"

PLAIN_LYRICS = "First line of lyrics\nSecond line of lyrics\nThird line of lyrics"
SYNCED_LYRICS = "[00:01.00]First synced line\n[00:12.34]Second synced line\n[00:23.45]Third"

ALL_FORMATS = ["mp3", "m4a", "flac", "ogg", "opus", "wav"]
VORBIS_FORMATS = ["flac", "ogg", "opus"]


# --- offline cover seams --------------------------------------------------


class FakeCoverDownloader:
    """Offline ``CoverDownloader`` returning committed synthetic JPEG bytes."""

    def __init__(self, data: bytes | None = FAKE_JPEG) -> None:
        self._data = data
        self.urls: list[str] = []

    def fetch(self, url: str) -> bytes | None:
        self.urls.append(url)
        return self._data


class FailingCoverDownloader:
    """Simulates a fetch failure: returns None, never raises (seam contract)."""

    def fetch(self, url: str) -> bytes | None:
        return None


# --- fixtures / helpers ---------------------------------------------------


def _track(
    *,
    lyrics_cover_url: str | None = "https://img/track-cover.jpg",
) -> Track:
    return Track(
        name="Test Title",
        artists=("First Artist", "Second Artist"),
        duration_ms=210_000,
        album=AlbumRef(
            name="Test Album",
            album_artist="Album Artist",
            year=2020,
            track_count=12,
            disc_count=2,
            cover_url="https://img/album-cover.jpg",
        ),
        isrc="USABC1234567",
        explicit=True,
        track_number=3,
        disc_number=1,
        genres=("indie rock", "dream pop"),
        year=2020,
        date="2020-05-01",
        publisher="Some Label",
        copyright_text="2020 Some Label",
        popularity=80,
        cover_url=lyrics_cover_url,
        provider=ProviderId.SPOTIFY,
        provider_id="sp123",
    )


def _request(
    fmt: str,
    *,
    track: Track | None = None,
    lyrics: Lyrics | None = None,
    embed_lyrics: bool = True,
    skip_album_art: bool = False,
) -> DownloadRequest:
    return DownloadRequest(
        track=track if track is not None else _track(),
        candidate=AudioCandidate(
            provider=ProviderId.YTMUSIC,
            provider_id="abc123",
            url=SOURCE_URL,
            name="Test Title",
        ),
        output_template="",
        output_format=OutputFormat(fmt),
        lyrics=lyrics,
        embed_lyrics=embed_lyrics,
        skip_album_art=skip_album_art,
        track_url=TRACK_URL,
    )


def _prep(silent_audio: dict[str, Path], tmp_path: Path, fmt: str) -> Path:
    """Copy the shared silent file to a fresh per-test path (embedding mutates)."""
    dst = tmp_path / f"track.{fmt}"
    shutil.copy(silent_audio[fmt], dst)
    return dst


# --- normalized readback --------------------------------------------------


def _read(path: Path, fmt: str) -> dict[str, object]:
    """Re-open ``path`` with mutagen and normalize the common logical fields."""
    if fmt == "mp3":
        from mutagen.id3 import ID3

        tags = ID3(str(path))
        return {
            "title": tags["TIT2"].text[0],
            "artist": tags["TPE1"].text[0],
            "album": tags["TALB"].text[0],
            "albumartist": tags["TPE2"].text[0],
            "genre": tags["TCON"].text[0],
            "tracknumber": tags["TRCK"].text[0],
            "discnumber": tags["TPOS"].text[0],
            "isrc": tags["TSRC"].text[0],
            "date": str(tags["TDRC"].text[0]),
            "woas": tags["WOAS"].url,
            "source": " ".join(t for c in tags.getall("COMM") for t in c.text),
            "has_cover": bool(tags.getall("APIC")),
        }
    if fmt == "m4a":
        from mutagen.mp4 import MP4

        tags = MP4(str(path))
        trk = tags["trkn"][0]
        dsk = tags["disk"][0]
        return {
            "title": tags["\xa9nam"][0],
            "artist": tags["\xa9ART"][0],
            "album": tags["\xa9alb"][0],
            "albumartist": tags["aART"][0],
            "genre": tags["\xa9gen"][0],
            "tracknumber": f"{trk[0]}/{trk[1]}",
            "discnumber": f"{dsk[0]}/{dsk[1]}",
            "isrc": bytes(tags["----:spotdl:ISRC"][0]).decode("utf-8"),
            "date": tags["\xa9day"][0],
            "woas": bytes(tags["----:spotdl:WOAS"][0]).decode("utf-8"),
            "source": tags["\xa9cmt"][0],
            "has_cover": bool(tags.get("covr")),
        }
    if fmt in VORBIS_FORMATS:
        import mutagen

        tags = mutagen.File(str(path))
        has_cover = bool(tags.pictures) if fmt == "flac" else "metadata_block_picture" in tags
        return {
            "title": tags["title"][0],
            "artist": tags["artist"][0],
            "album": tags["album"][0],
            "albumartist": tags["albumartist"][0],
            "genre": tags["genre"][0],
            "tracknumber": f"{tags['tracknumber'][0]}/{tags['tracktotal'][0]}",
            "discnumber": f"{tags['discnumber'][0]}/{tags['disctotal'][0]}",
            "isrc": tags["isrc"][0],
            "date": tags["date"][0],
            "woas": tags["woas"][0],
            "source": tags["comment"][0],
            "has_cover": has_cover,
        }
    if fmt == "wav":
        from mutagen.wave import WAVE

        tags = WAVE(str(path)).tags
        return {
            "title": tags["TIT2"].text[0],
            "artist": tags["TPE1"].text[0],
            "album": tags["TALB"].text[0],
            "genre": tags["TCON"].text[0],
            "tracknumber": tags["TRCK"].text[0],
            "isrc": tags["TSRC"].text[0],
            "date": str(tags["TDRC"].text[0]),
            "woas": tags["WOAS"].url,
            "source": " ".join(t for c in tags.getall("COMM") for t in c.text),
            "has_cover": bool(tags.getall("APIC")),
        }
    raise AssertionError(fmt)


# --- contract: preset tables ----------------------------------------------


def test_mp3_preset_is_contract() -> None:
    assert MP3_TAG_PRESET["album"] == "TALB"
    assert MP3_TAG_PRESET["artist"] == "TPE1"
    assert MP3_TAG_PRESET["title"] == "TIT2"
    assert MP3_TAG_PRESET["albumartist"] == "TPE2"
    assert MP3_TAG_PRESET["genre"] == "TCON"
    assert MP3_TAG_PRESET["tracknumber"] == "TRCK"
    assert MP3_TAG_PRESET["discnumber"] == "TPOS"
    assert MP3_TAG_PRESET["isrc"] == "TSRC"
    assert MP3_TAG_PRESET["woas"] == "WOAS"
    assert MP3_TAG_PRESET["copyright"] == "TCOP"
    assert MP3_TAG_PRESET["albumart"] == "APIC"


def test_m4a_preset_is_contract() -> None:
    assert M4A_TAG_PRESET["album"] == "\xa9alb"
    assert M4A_TAG_PRESET["artist"] == "\xa9ART"
    assert M4A_TAG_PRESET["title"] == "\xa9nam"
    assert M4A_TAG_PRESET["albumartist"] == "aART"
    assert M4A_TAG_PRESET["tracknumber"] == "trkn"
    assert M4A_TAG_PRESET["discnumber"] == "disk"
    assert M4A_TAG_PRESET["albumart"] == "covr"
    assert M4A_TAG_PRESET["woas"] == "----:spotdl:WOAS"
    assert M4A_TAG_PRESET["isrc"] == "----:spotdl:ISRC"
    assert M4A_TAG_PRESET["explicit"] == "rtng"


def test_lrc_regex_detects_timestamps() -> None:
    assert LRC_REGEX.match("[00:12.34]hello")
    assert not LRC_REGEX.match("plain lyric line")


# --- core field parity across every container -----------------------------


@pytest.mark.parametrize("fmt", ALL_FORMATS)
def test_common_fields_embedded(silent_audio: dict[str, Path], tmp_path: Path, fmt: str) -> None:
    path = _prep(silent_audio, tmp_path, fmt)
    embed_metadata(path, _request(fmt), FakeCoverDownloader())
    got = _read(path, fmt)

    assert got["title"] == "Test Title"
    assert "First Artist" in str(got["artist"])
    assert got["album"] == "Test Album"
    assert got["genre"] == "Indie Rock"  # title-cased first genre
    assert got["tracknumber"] == "3/12"
    assert got["isrc"] == "USABC1234567"
    assert got["date"] == "2020-05-01"
    assert got["woas"] == TRACK_URL  # canonical track link
    assert SOURCE_URL in str(got["source"])  # audio source (candidate.url)


@pytest.mark.parametrize("fmt", ["mp3", "m4a", "flac", "ogg", "opus"])
def test_albumartist_and_discnumber(
    silent_audio: dict[str, Path], tmp_path: Path, fmt: str
) -> None:
    path = _prep(silent_audio, tmp_path, fmt)
    embed_metadata(path, _request(fmt), FakeCoverDownloader())
    got = _read(path, fmt)
    assert got["albumartist"] == "Album Artist"
    assert got["discnumber"] == "1/2"


def test_m4a_explicit_rating(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    from mutagen.mp4 import MP4

    path = _prep(silent_audio, tmp_path, "m4a")
    embed_metadata(path, _request("m4a"), FakeCoverDownloader())
    assert MP4(str(path))["rtng"] == [4]  # 4 == explicit


def test_m4a_clean_rating(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    from mutagen.mp4 import MP4

    track = _track().model_copy(update={"explicit": False})
    path = _prep(silent_audio, tmp_path, "m4a")
    embed_metadata(path, _request("m4a", track=track), FakeCoverDownloader())
    assert MP4(str(path))["rtng"] == [2]  # 2 == clean


# --- mp3 popularity + lyrics ----------------------------------------------


def test_mp3_popularity_popm(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    from mutagen.id3 import ID3

    path = _prep(silent_audio, tmp_path, "mp3")
    embed_metadata(path, _request("mp3"), FakeCoverDownloader())
    popm = ID3(str(path)).getall("POPM")
    assert popm
    assert popm[0].rating == int(80 * 255 / 100)  # 204


def test_mp3_plain_lyrics_uslt(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    from mutagen.id3 import ID3

    lyrics = Lyrics(kind=LyricsKind.PLAIN, text=PLAIN_LYRICS, source=ProviderId.GENIUS)
    path = _prep(silent_audio, tmp_path, "mp3")
    embed_metadata(path, _request("mp3", lyrics=lyrics), FakeCoverDownloader())
    tags = ID3(str(path))
    uslt = tags.getall("USLT")
    assert uslt
    assert "First line of lyrics" in uslt[0].text
    assert not tags.getall("SYLT")


def test_mp3_synced_lyrics_sylt(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    from mutagen.id3 import ID3

    lyrics = Lyrics(kind=LyricsKind.SYNCED, text=SYNCED_LYRICS, source=ProviderId.LRCLIB)
    path = _prep(silent_audio, tmp_path, "mp3")
    embed_metadata(path, _request("mp3", lyrics=lyrics), FakeCoverDownloader())
    tags = ID3(str(path))
    sylt = tags.getall("SYLT")
    assert sylt
    # SYLT carries the parsed (text, ms) pairs; cleaned USLT accompanies it.
    assert sylt[0].text
    assert any(text and ms >= 0 for text, ms in sylt[0].text)
    uslt = tags.getall("USLT")
    assert uslt
    assert "[00:" not in uslt[0].text  # timestamps stripped from the plain copy


def test_synced_detection_uses_regex_not_kind(
    silent_audio: dict[str, Path], tmp_path: Path
) -> None:
    from mutagen.id3 import ID3

    # kind says PLAIN but text is actually LRC -> regex detection wins (v4 parity).
    lyrics = Lyrics(kind=LyricsKind.PLAIN, text=SYNCED_LYRICS, source=ProviderId.LRCLIB)
    path = _prep(silent_audio, tmp_path, "mp3")
    embed_metadata(path, _request("mp3", lyrics=lyrics), FakeCoverDownloader())
    assert ID3(str(path)).getall("SYLT")


def test_vorbis_plain_lyrics(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    import mutagen

    lyrics = Lyrics(kind=LyricsKind.PLAIN, text=PLAIN_LYRICS, source=ProviderId.GENIUS)
    path = _prep(silent_audio, tmp_path, "flac")
    embed_metadata(path, _request("flac", lyrics=lyrics), FakeCoverDownloader())
    assert "First line of lyrics" in mutagen.File(str(path))["lyrics"][0]


def test_embed_lyrics_disabled(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    import mutagen

    lyrics = Lyrics(kind=LyricsKind.PLAIN, text=PLAIN_LYRICS, source=ProviderId.GENIUS)
    path = _prep(silent_audio, tmp_path, "flac")
    embed_metadata(path, _request("flac", lyrics=lyrics, embed_lyrics=False), FakeCoverDownloader())
    assert "lyrics" not in mutagen.File(str(path))


# --- cover art seam -------------------------------------------------------


@pytest.mark.parametrize("fmt", ALL_FORMATS)
def test_cover_embedded(silent_audio: dict[str, Path], tmp_path: Path, fmt: str) -> None:
    path = _prep(silent_audio, tmp_path, fmt)
    cover = FakeCoverDownloader()
    embed_metadata(path, _request(fmt), cover)
    assert _read(path, fmt)["has_cover"] is True
    assert cover.urls  # the seam was actually consulted


def test_cover_prefers_track_cover(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    # retain-track-cover honoured: track.cover_url wins over album.cover_url.
    path = _prep(silent_audio, tmp_path, "flac")
    cover = FakeCoverDownloader()
    embed_metadata(path, _request("flac"), cover)
    assert cover.urls == ["https://img/track-cover.jpg"]


def test_cover_falls_back_to_album(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    path = _prep(silent_audio, tmp_path, "flac")
    cover = FakeCoverDownloader()
    embed_metadata(path, _request("flac", track=_track(lyrics_cover_url=None)), cover)
    assert cover.urls == ["https://img/album-cover.jpg"]


@pytest.mark.parametrize("fmt", ALL_FORMATS)
def test_skip_album_art(silent_audio: dict[str, Path], tmp_path: Path, fmt: str) -> None:
    path = _prep(silent_audio, tmp_path, fmt)
    cover = FakeCoverDownloader()
    embed_metadata(path, _request(fmt, skip_album_art=True), cover)
    assert _read(path, fmt)["has_cover"] is False
    assert cover.urls == []  # never fetched when skipping art


@pytest.mark.parametrize("fmt", ALL_FORMATS)
def test_cover_failure_is_swallowed(
    silent_audio: dict[str, Path], tmp_path: Path, fmt: str
) -> None:
    # Fetch returns None -> no cover, but the rest of the tags still save.
    path = _prep(silent_audio, tmp_path, fmt)
    embed_metadata(path, _request(fmt), FailingCoverDownloader())
    got = _read(path, fmt)
    assert got["has_cover"] is False
    assert got["title"] == "Test Title"  # tags still written


# --- error handling -------------------------------------------------------


def test_unknown_suffix_raises(tmp_path: Path) -> None:
    path = tmp_path / "track.xyz"
    path.write_bytes(b"not audio")
    with pytest.raises(MetadataEmbedFailed):
        embed_metadata(path, _request("mp3"), FakeCoverDownloader())


def test_corrupt_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_bytes(b"this is not a flac file at all")
    with pytest.raises(MetadataEmbedFailed):
        embed_metadata(path, _request("flac"), FakeCoverDownloader())


# --- HttpCoverDownloader (offline: no network exercised) ------------------


def test_http_cover_downloader_is_protocol() -> None:
    dl = HttpCoverDownloader(proxy=None, timeout=1.0)
    assert isinstance(dl, CoverDownloader)


def test_http_cover_downloader_swallows_errors() -> None:
    # A malformed URL must return None, never raise (seam contract).
    dl = HttpCoverDownloader(timeout=0.01)
    assert dl.fetch("http://") is None


# --- EmbedStep ------------------------------------------------------------


async def test_embed_step_runs_and_reports(silent_audio: dict[str, Path], tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadContext

    path = _prep(silent_audio, tmp_path, "mp3")
    events: list[ProgressEvent] = []
    ctx = DownloadContext(request=_request("mp3"), final_path=path)
    step = EmbedStep(FakeCoverDownloader(), on_progress=events.append)
    out = await step(ctx)
    assert out.request == ctx.request
    assert any(e.phase is ProgressPhase.EMBED for e in events)
    # tags actually landed
    from mutagen.id3 import ID3

    assert ID3(str(path))["TIT2"].text[0] == "Test Title"


async def test_embed_step_wraps_errors(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadContext

    path = tmp_path / "track.xyz"
    path.write_bytes(b"garbage")
    ctx = DownloadContext(request=_request("mp3"), final_path=path)
    step = EmbedStep(FakeCoverDownloader())
    with pytest.raises(MetadataEmbedFailed):
        await step(ctx)
