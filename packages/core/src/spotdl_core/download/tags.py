"""Metadata embedding for the six output containers via mutagen.

Ports v4's ``spotdl/utils/metadata.py`` (``MP3_TAG_PRESET``, ``M4A_TAG_PRESET``,
the vorbis-comment keys for flac/ogg/opus, ``embed_metadata``, ``embed_cover``,
``embed_lyrics``, ``embed_wav_file``, ``LRC_REGEX``) against the v5 domain model.

The per-container tag-preset tables (``MP3_TAG_PRESET``, ``M4A_TAG_PRESET``) are a
CONTRACT: other tools read these exact frames/atoms, so the logical->container-key
mapping must stay stable.

Cover art is fetched through an injectable :class:`CoverDownloader` seam so the
default test suite is fully offline; the shipped :class:`HttpCoverDownloader` uses
the stdlib and honours a proxy. mutagen imports are deferred to call time so
``import spotdl_core.download.tags`` never fails when a codec-specific submodule is
absent, mirroring the fetch/convert steps.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from spotdl_core.download.context import (
    DownloadContext,
    DownloadRequest,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
)
from spotdl_core.model import Track
from spotdl_core.providers.errors import MetadataEmbedFailed

__all__ = [
    "LRC_REGEX",
    "M4A_TAG_PRESET",
    "MP3_TAG_PRESET",
    "CoverDownloader",
    "EmbedStep",
    "HttpCoverDownloader",
    "embed_metadata",
]

# --- CONTRACT: per-container tag-preset tables ----------------------------

# logical field -> ID3 frame id (ID3v2). Ported from v4 ``MP3_TAG_PRESET``.
MP3_TAG_PRESET: dict[str, str] = {
    "album": "TALB",
    "artist": "TPE1",
    "date": "TDRC",
    "title": "TIT2",
    "year": "TYER",
    "comment": "COMM",
    "group": "TIT1",
    "writer": "TEXT",
    "genre": "TCON",
    "tracknumber": "TRCK",
    "trackcount": "TRCK",
    "albumartist": "TPE2",
    "discnumber": "TPOS",
    "disccount": "TPOS",
    "compilation": "TCMP",
    "albumart": "APIC",
    "encodedby": "TENC",
    "copyright": "TCOP",
    "tempo": "TBPM",
    "lyrics": "USLT",
    "woas": "WOAS",
    "isrc": "TSRC",
    "popularity": "POPM",
}

# logical field -> MP4 atom. Ported from v4 ``M4A_TAG_PRESET`` (Apple atoms;
# ``\xa9`` is the copyright-sign prefix, ``----:...`` are freeform atoms).
M4A_TAG_PRESET: dict[str, str] = {
    "album": "\xa9alb",
    "artist": "\xa9ART",
    "date": "\xa9day",
    "title": "\xa9nam",
    "year": "\xa9day",
    "comment": "\xa9cmt",
    "group": "\xa9grp",
    "writer": "\xa9wrt",
    "genre": "\xa9gen",
    "tracknumber": "trkn",
    "trackcount": "trkn",
    "albumartist": "aART",
    "discnumber": "disk",
    "disccount": "disk",
    "compilation": "cpil",
    "albumart": "covr",
    "encodedby": "\xa9too",
    "copyright": "cprt",
    "tempo": "tmpo",
    "lyrics": "\xa9lyr",
    "explicit": "rtng",
    "woas": "----:spotdl:WOAS",
    "isrc": "----:spotdl:ISRC",
}

# Detects an LRC timestamp ``[mm:ss.xx]`` at the start of a line.
LRC_REGEX: re.Pattern[str] = re.compile(r"(\[\d{2}:\d{2}\.\d{2,3}\])")


# --- cover-download seam --------------------------------------------------


@runtime_checkable
class CoverDownloader(Protocol):
    """Fetches cover-art bytes. Returns ``None`` on any failure; never raises."""

    def fetch(self, url: str) -> bytes | None: ...


class HttpCoverDownloader:
    """Default :class:`CoverDownloader` using the stdlib ``urllib`` with an
    optional HTTP(S) proxy. Swallows every error into ``None`` so a flaky cover
    host can never break tag embedding."""

    def __init__(self, proxy: str | None = None, timeout: float = 10.0) -> None:
        self._proxy = proxy
        self._timeout = timeout

    def fetch(self, url: str) -> bytes | None:
        import urllib.request

        try:
            if self._proxy:
                handler = urllib.request.ProxyHandler({"http": self._proxy, "https": self._proxy})
                opener = urllib.request.build_opener(handler)
            else:
                opener = urllib.request.build_opener()
            with opener.open(url, timeout=self._timeout) as response:
                data: bytes = response.read()
            return data
        except Exception:
            return None


# --- derived helpers ------------------------------------------------------


def _album_artist(track: Track) -> str:
    if track.album is not None and track.album.album_artist:
        return track.album.album_artist
    return track.main_artist


def _track_count(track: Track) -> int | None:
    return track.album.track_count if track.album is not None else None


def _disc_count(track: Track) -> int | None:
    return track.album.disc_count if track.album is not None else None


def _album_name(track: Track) -> str | None:
    return track.album.name if track.album is not None else None


def _num_total(num: int, total: int | None) -> str:
    return f"{num}/{total}" if total is not None else str(num)


def _cover_url(track: Track) -> str | None:
    # Prefer the track-level cover (honours retain-track-cover), fall back to
    # the album cover.
    if track.cover_url:
        return track.cover_url
    if track.album is not None:
        return track.album.cover_url
    return None


def _cover_bytes(request: DownloadRequest, cover: CoverDownloader) -> bytes | None:
    if request.skip_album_art:
        return None
    url = _cover_url(request.track)
    if not url:
        return None
    try:
        return cover.fetch(url)
    except Exception:
        # The protocol says fetch never raises, but a misbehaving downloader
        # must still not break tag saving (v4 swallowed cover errors).
        return None


def _lyrics_text(request: DownloadRequest) -> str | None:
    if not request.embed_lyrics or request.lyrics is None:
        return None
    return request.lyrics.text or None


def _remove_lrc(lyrics: str) -> str:
    """Strip ``[...]`` LRC tags, leaving plain lyric text (v4 ``remomve_lrc``)."""
    return re.sub(r"\[.*?\]", "", lyrics)


def _is_synced(lyrics: str) -> bool:
    """LRC vs plain detection via ``LRC_REGEX`` on the first 5 lines (v4 parity:
    the regex is authoritative, ``Lyrics.kind`` is only a hint)."""
    return any(line and LRC_REGEX.match(line) for line in lyrics.splitlines()[:5])


def _parse_lrc(lyrics: str) -> list[tuple[str, int]]:
    """Parse ``[mm:ss.xx]text`` lines into ``(text, milliseconds)`` pairs for
    SYLT. Malformed timestamps are skipped."""
    data: list[tuple[str, int]] = []
    for line in lyrics.splitlines():
        time_tag = line.split("]", 1)[0] + "]"
        text = line.replace(time_tag, "")
        cleaned = time_tag.strip("[]").replace(".", ":")
        parts = cleaned.split(":")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            continue
        minute, second, millis = (int(part) for part in parts)
        data.append((text, minute * 60_000 + second * 1_000 + millis))
    return data


# --- ID3 lyrics (shared by mp3 + wav) -------------------------------------


def _embed_id3_lyrics(tags: Any, request: DownloadRequest) -> None:
    from mutagen.id3._frames import SYLT, USLT
    from mutagen.id3._specs import Encoding

    text = _lyrics_text(request)
    if not text:
        return
    if _is_synced(text):
        tags.add(USLT(encoding=Encoding.UTF8, text=_remove_lrc(text)))
        tags.add(SYLT(encoding=3, format=2, type=1, text=_parse_lrc(text)))
    else:
        tags.add(USLT(encoding=Encoding.UTF8, text=text))


# --- per-container embedders ----------------------------------------------


def _embed_mp3(output_file: Path, request: DownloadRequest, cover: CoverDownloader) -> None:
    from mutagen.id3 import ID3, ID3NoHeaderError
    from mutagen.id3._frames import (
        APIC,
        COMM,
        POPM,
        TALB,
        TCON,
        TCOP,
        TDRC,
        TENC,
        TIT2,
        TPE1,
        TPE2,
        TPOS,
        TRCK,
        TSRC,
        TYER,
        WOAS,
    )

    track = request.track
    try:
        tags = ID3(str(output_file))
    except ID3NoHeaderError:
        tags = ID3()

    tags.setall("TPE1", [TPE1(encoding=3, text=list(track.artists))])
    tags.setall("TPE2", [TPE2(encoding=3, text=_album_artist(track))])
    tags.setall("TIT2", [TIT2(encoding=3, text=track.name)])
    if track.date:
        tags.setall("TDRC", [TDRC(encoding=3, text=track.date)])
    if track.publisher:
        tags.setall("TENC", [TENC(encoding=3, text=track.publisher)])
    name = _album_name(track)
    if name:
        tags.setall("TALB", [TALB(encoding=3, text=name)])
    if track.genres:
        tags.setall("TCON", [TCON(encoding=3, text=track.genres[0].title())])
    if track.copyright_text:
        tags.setall("TCOP", [TCOP(encoding=3, text=track.copyright_text)])
    if track.track_number is not None:
        tags.setall(
            "TRCK", [TRCK(encoding=3, text=_num_total(track.track_number, _track_count(track)))]
        )
    if track.disc_number is not None:
        tags.setall(
            "TPOS", [TPOS(encoding=3, text=_num_total(track.disc_number, _disc_count(track)))]
        )
    if track.isrc:
        tags.setall("TSRC", [TSRC(encoding=3, text=track.isrc)])
    if request.track_url:
        tags.setall("WOAS", [WOAS(encoding=3, url=request.track_url)])
    if request.candidate.url:
        tags.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=request.candidate.url)])
    if track.popularity:
        tags.setall("POPM", [POPM(rating=int(track.popularity * 255 / 100))])
    if track.year:
        tags.setall("TYER", [TYER(encoding=3, text=str(track.year))])

    cover_data = _cover_bytes(request, cover)
    if cover_data:
        tags.setall(
            "APIC",
            [APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data)],
        )

    _embed_id3_lyrics(tags, request)

    separator = request.id3_separator
    if separator != "/":
        tags.save(str(output_file), v2_version=3, v23_sep=separator)
    else:
        tags.save(str(output_file), v2_version=3)


def _embed_m4a(output_file: Path, request: DownloadRequest, cover: CoverDownloader) -> None:
    from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm

    track = request.track
    preset = M4A_TAG_PRESET
    audio = MP4(str(output_file))

    audio[preset["artist"]] = list(track.artists)
    audio[preset["albumartist"]] = [_album_artist(track)]
    audio[preset["title"]] = [track.name]
    if track.date:
        audio[preset["date"]] = [track.date]
    if track.publisher:
        audio[preset["encodedby"]] = [track.publisher]
    name = _album_name(track)
    if name:
        audio[preset["album"]] = [name]
    if track.genres:
        audio[preset["genre"]] = [track.genres[0].title()]
    if track.copyright_text:
        audio[preset["copyright"]] = [track.copyright_text]
    if request.candidate.url:
        audio[preset["comment"]] = [request.candidate.url]
    if track.disc_number is not None:
        audio[preset["discnumber"]] = [(track.disc_number, _disc_count(track) or 0)]
    if track.track_number is not None:
        audio[preset["tracknumber"]] = [(track.track_number, _track_count(track) or 0)]
    audio[preset["explicit"]] = [4 if track.explicit else 2]
    if request.track_url:
        audio[preset["woas"]] = [MP4FreeForm(request.track_url.encode("utf-8"))]
    if track.isrc:
        audio[preset["isrc"]] = [MP4FreeForm(track.isrc.encode("utf-8"))]

    cover_data = _cover_bytes(request, cover)
    if cover_data:
        audio[preset["albumart"]] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    text = _lyrics_text(request)
    if text:
        # m4a has no synced-lyric atom; store the lyrics text verbatim (v4 parity).
        audio[preset["lyrics"]] = [text]

    audio.save()


def _embed_vorbis(
    output_file: Path, request: DownloadRequest, cover: CoverDownloader, suffix: str
) -> None:
    import mutagen

    track = request.track
    audio = mutagen.File(str(output_file))
    if audio is None:
        raise MetadataEmbedFailed(f"Unrecognized file format for {output_file}")

    audio["artist"] = list(track.artists)
    audio["albumartist"] = _album_artist(track)
    audio["title"] = track.name
    if track.date:
        audio["date"] = track.date
    if track.publisher:
        audio["encodedby"] = track.publisher
    name = _album_name(track)
    if name:
        audio["album"] = name
    if track.genres:
        audio["genre"] = track.genres[0].title()
    if track.copyright_text:
        audio["copyright"] = track.copyright_text
    if request.candidate.url:
        audio["comment"] = request.candidate.url
    if track.disc_number is not None:
        audio["discnumber"] = str(track.disc_number)
    disc_count = _disc_count(track)
    if disc_count is not None:
        audio["disctotal"] = str(disc_count)
    track_count = _track_count(track)
    if track_count is not None:
        audio["tracktotal"] = str(track_count)
    if track.track_number is not None:
        audio["tracknumber"] = str(track.track_number)
    if request.track_url:
        audio["woas"] = request.track_url
    if track.isrc:
        audio["isrc"] = track.isrc

    cover_data = _cover_bytes(request, cover)
    if cover_data:
        _embed_vorbis_cover(audio, cover_data, suffix)

    text = _lyrics_text(request)
    if text:
        audio["lyrics"] = text

    audio.save()


def _embed_vorbis_cover(audio: Any, cover_data: bytes, suffix: str) -> None:
    from mutagen.flac import Picture

    picture = Picture()
    picture.type = 3
    picture.desc = "Cover"
    picture.mime = "image/jpeg"
    picture.data = cover_data

    if suffix == "flac":
        if audio.pictures:
            audio.clear_pictures()
        audio.add_picture(picture)
    else:
        encoded = base64.b64encode(picture.write()).decode("ascii")
        audio["metadata_block_picture"] = [encoded]


def _embed_wav(output_file: Path, request: DownloadRequest, cover: CoverDownloader) -> None:
    from mutagen.id3._frames import (
        APIC,
        COMM,
        TALB,
        TCOM,
        TCON,
        TCOP,
        TDRC,
        TIT2,
        TPE1,
        TRCK,
        TSRC,
        WOAS,
    )
    from mutagen.wave import WAVE

    track = request.track
    audio = WAVE(str(output_file))
    if audio.tags is None:
        audio.add_tags()
    else:
        audio.tags.clear()
    tags = audio.tags

    tags.add(TIT2(encoding=3, text=track.name))
    tags.add(TPE1(encoding=3, text=list(track.artists)))
    name = _album_name(track)
    if name:
        tags.add(TALB(encoding=3, text=name))
    if track.publisher:
        tags.add(TCOM(encoding=3, text=track.publisher))
    if track.genres:
        tags.add(TCON(encoding=3, text=[genre.title() for genre in track.genres]))
    if track.date:
        tags.add(TDRC(encoding=3, text=track.date))
    if track.track_number is not None:
        tags.add(TRCK(encoding=3, text=_num_total(track.track_number, _track_count(track))))
    if request.track_url:
        tags.add(WOAS(encoding=3, url=request.track_url))
    if track.isrc:
        tags.add(TSRC(encoding=3, text=track.isrc))
    if request.candidate.url:
        tags.add(COMM(encoding=3, lang="eng", desc="", text=request.candidate.url))
    if track.copyright_text:
        tags.add(TCOP(encoding=3, text=track.copyright_text))
    if track.popularity:
        tags.add(
            COMM(
                encoding=3,
                lang="eng",
                desc="popularity",
                text=f"Spotify Popularity: {track.popularity}",
            )
        )

    cover_data = _cover_bytes(request, cover)
    if cover_data:
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data))

    _embed_id3_lyrics(tags, request)

    audio.save()


# --- dispatch -------------------------------------------------------------

_EMBEDDERS = {
    "mp3": _embed_mp3,
    "m4a": _embed_m4a,
    "wav": _embed_wav,
}


def embed_metadata(output_file: Path, request: DownloadRequest, cover: CoverDownloader) -> None:
    """Embed ``request`` metadata into ``output_file`` (dispatched by suffix).

    Raises :class:`MetadataEmbedFailed` on an unknown suffix, an unrecognized/
    corrupt file, or any mutagen error. A cover-download failure is swallowed —
    the remaining tags are still saved.
    """
    suffix = output_file.suffix.lower().lstrip(".")
    try:
        if suffix in ("flac", "ogg", "opus"):
            _embed_vorbis(output_file, request, cover, suffix)
        else:
            embedder = _EMBEDDERS.get(suffix)
            if embedder is None:
                raise MetadataEmbedFailed(f"Unsupported container: {output_file.suffix!r}")
            embedder(output_file, request, cover)
    except MetadataEmbedFailed:
        raise
    except Exception as exc:
        raise MetadataEmbedFailed(
            f"Failed to embed metadata into {output_file.name}: {exc}"
        ) from exc


# --- pipeline step --------------------------------------------------------


class EmbedStep:
    """Pipeline step that embeds metadata into ``ctx.final_path`` off-thread and
    emits an ``EMBED`` progress event. Returns the context unchanged."""

    def __init__(self, cover: CoverDownloader, on_progress: ProgressCallback | None = None) -> None:
        self._cover = cover
        self._on_progress = on_progress

    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        self._emit(ProgressEvent(phase=ProgressPhase.EMBED))
        path = ctx.final_path
        if path is None:
            raise MetadataEmbedFailed("no output file to embed metadata into")
        try:
            await asyncio.to_thread(embed_metadata, path, ctx.request, self._cover)
        except MetadataEmbedFailed:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrap
            raise MetadataEmbedFailed(str(exc)) from exc
        return ctx

    def _emit(self, event: ProgressEvent) -> None:
        if self._on_progress is None:
            return
        # Progress is best-effort; a bad callback must never break the step.
        with contextlib.suppress(Exception):
            self._on_progress(event)
