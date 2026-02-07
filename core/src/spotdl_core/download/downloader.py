"""Shared download engine using yt-dlp and mutagen for metadata embedding.

Used by both CLI and backend. Settings-agnostic: takes a DownloadSettings
dataclass that each consumer constructs from their own config source.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import shlex
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when a download fails."""


@dataclass
class DownloadSettings:
    """Settings that control download behaviour.

    Both CLI (from its pydantic Settings) and backend (from the DB
    UserSettings row) build this dataclass so the downloader itself
    stays decoupled from any particular config source.
    """

    audio_format: str = "mp3"
    audio_quality: str = "best"
    bitrate: str | None = None
    output_template: str = "{artist} - {title}"
    max_filename_length: int = 255
    restrict: str | None = None
    overwrite: str = "skip"
    embed_metadata: bool = True
    embed_lyrics: bool = True
    embed_cover: bool = True
    id3_separator: str = "/"
    sponsor_block: bool = False
    sponsor_block_categories: list[str] = field(default_factory=lambda: [
        "sponsor", "intro", "outro", "selfpromo", "preview", "filler",
        "interaction",
    ])
    generate_lrc: bool = False
    playlist_numbering: bool = False
    skip_explicit: bool = False
    ffmpeg_args: str | None = None
    yt_dlp_args: str | None = None
    proxy: str | None = None
    cookies_path: Path | None = None
    archive: str | None = None


@dataclass
class DownloadProgress:
    """Progress information emitted during a download."""

    status: str = ""
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""


@dataclass
class DownloadMeta:
    """Song metadata passed to the downloader for filename templating and embedding."""

    title: str = ""
    artist: str = ""
    artists: list[str] = field(default_factory=list)
    album: str | None = None
    album_artist: str | None = None
    cover_url: str | None = None
    duration: int | None = None
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    date: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    disc_count: int | None = None
    tracks_count: int | None = None
    isrc: str | None = None
    publisher: str | None = None
    song_id: str | None = None
    song_url: str | None = None
    lyrics: str | None = None
    explicit: bool | None = None
    # list context
    list_name: str | None = None
    list_position: int | None = None
    list_length: int | None = None


class Downloader:
    """Async download engine backed by yt-dlp with multi-format metadata embedding."""

    def __init__(self, settings: DownloadSettings | None = None) -> None:
        self._settings = settings or DownloadSettings()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            kwargs: dict[str, Any] = {"timeout": 30.0, "follow_redirects": True}
            if self._settings.proxy:
                kwargs["proxy"] = self._settings.proxy
            self._http_client = httpx.AsyncClient(**kwargs)
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ── filename templating ─────────────────────────────────────────

    def get_output_template(self, meta: DownloadMeta) -> str:
        """Generate output filename from template + metadata."""
        template = self._settings.output_template
        first_artist = meta.artists[0] if meta.artists else meta.artist

        replacements = {
            "{artist}": first_artist,
            "{artists}": ", ".join(meta.artists) if meta.artists else meta.artist,
            "{title}": meta.title,
            "{album}": meta.album or "Unknown",
            "{album-artist}": meta.album_artist or first_artist,
            "{genre}": meta.genres[0] if meta.genres else "",
            "{year}": str(meta.year) if meta.year else "Unknown",
            "{track-number}": str(meta.track_number).zfill(2) if meta.track_number else "00",
            "{track_number}": str(meta.track_number).zfill(2) if meta.track_number else "00",
            "{disc-number}": str(meta.disc_number) if meta.disc_number else "1",
            "{disc_number}": str(meta.disc_number) if meta.disc_number else "1",
            "{disc-count}": str(meta.disc_count) if meta.disc_count else "1",
            "{duration}": str(meta.duration) if meta.duration else "0",
            "{original-date}": meta.date or "",
            "{tracks-count}": str(meta.tracks_count) if meta.tracks_count else "",
            "{isrc}": meta.isrc or "",
            "{track-id}": meta.song_id or "",
            "{publisher}": meta.publisher or "",
            "{list-length}": str(meta.list_length) if meta.list_length else "",
            "{list-position}": f"{meta.list_position:02d}" if meta.list_position else "",
            "{list-name}": meta.list_name or "",
            "{output-ext}": self._settings.audio_format,
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, self.sanitize_filename(value))

        if self._settings.playlist_numbering and meta.list_position:
            result = f"{meta.list_position:02d}. {result}"

        result = self._limit_filename_length(result, meta)
        return result

    def _limit_filename_length(self, result: str, meta: DownloadMeta) -> str:
        max_len = self._settings.max_filename_length
        ext_len = len(self._settings.audio_format) + 1

        if len(result) + ext_len <= max_len:
            return result

        short = f"{self.sanitize_filename(meta.artist)} - {self.sanitize_filename(meta.title)}"
        if len(short) + ext_len <= max_len:
            return short

        return short[: max_len - ext_len]

    def sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        restrict = self._settings.restrict

        if restrict == "strict":
            import yt_dlp
            return yt_dlp.utils.sanitize_filename(name, restricted=True) or "Unknown"
        elif restrict == "loose":
            normalized = unicodedata.normalize("NFKD", name)
            ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
            name = ascii_name or name

        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        name = name.strip(". ")
        if len(name) > 200:
            name = name[:200]
        return name or "Unknown"

    # ── yt-dlp options ──────────────────────────────────────────────

    def get_yt_dlp_options(
        self,
        output_path: Path,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
    ) -> dict[str, Any]:
        """Build yt-dlp option dict from current settings."""
        format_map = {
            "mp3": "mp3", "m4a": "m4a", "flac": "flac",
            "opus": "opus", "ogg": "vorbis", "wav": "wav",
        }
        codec = format_map.get(self._settings.audio_format, "mp3")

        quality_map = {"best": "0", "320k": "320", "256k": "256", "192k": "192", "128k": "128"}
        audio_quality = quality_map.get(self._settings.audio_quality, "0")

        bitrate = self._settings.bitrate
        if bitrate == "disable":
            codec = "best"
            audio_quality = "0"
        elif bitrate and bitrate != "auto":
            if bitrate.isdigit():
                audio_quality = bitrate
            else:
                audio_quality = bitrate.rstrip("kK")

        postprocessors: list[dict[str, Any]] = []
        if bitrate != "disable":
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": audio_quality,
            })

        if self._settings.sponsor_block:
            cats = self._settings.sponsor_block_categories
            postprocessors.extend([
                {"key": "SponsorBlock", "categories": cats},
                {"key": "ModifyChapters", "remove_sponsor_segments": cats},
            ])

        options: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(output_path),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "no_color": True,
            "extract_flat": False,
            "postprocessors": postprocessors,
        }

        if self._settings.cookies_path and self._settings.cookies_path.exists():
            options["cookiefile"] = str(self._settings.cookies_path)

        if self._settings.proxy:
            options["proxy"] = self._settings.proxy

        if self._settings.ffmpeg_args:
            options["postprocessor_args"] = {
                "ffmpeg": shlex.split(self._settings.ffmpeg_args),
            }

        if self._settings.yt_dlp_args:
            custom_args = shlex.split(self._settings.yt_dlp_args)
            i = 0
            while i < len(custom_args):
                arg = custom_args[i]
                if arg.startswith("--"):
                    key = arg[2:].replace("-", "_")
                    if i + 1 < len(custom_args) and not custom_args[i + 1].startswith("--"):
                        options[key] = custom_args[i + 1]
                        i += 2
                    else:
                        options[key] = True
                        i += 1
                else:
                    i += 1

        if progress_callback:
            def hook(d: dict[str, Any]) -> None:
                progress = DownloadProgress()
                progress.status = d.get("status", "")
                progress.filename = d.get("filename", "")

                if d.get("status") == "downloading":
                    if "downloaded_bytes" in d and "total_bytes" in d:
                        progress.progress = d["downloaded_bytes"] / d["total_bytes"] * 100
                    elif "downloaded_bytes" in d and "total_bytes_estimate" in d:
                        progress.progress = d["downloaded_bytes"] / d["total_bytes_estimate"] * 100
                    elif "_percent_str" in d:
                        try:
                            progress.progress = float(d["_percent_str"].strip().rstrip("%"))
                        except ValueError:
                            pass

                    if "_speed_str" in d:
                        progress.speed = d["_speed_str"].strip()
                    elif d.get("speed"):
                        progress.speed = _format_speed(d["speed"])

                    if "_eta_str" in d:
                        progress.eta = d["_eta_str"].strip()
                    elif d.get("eta"):
                        progress.eta = _format_eta(d["eta"])

                elif d.get("status") == "finished":
                    progress.progress = 100.0

                progress_callback(progress)

            options["progress_hooks"] = [hook]

        return options

    # ── download ────────────────────────────────────────────────────

    async def download(
        self,
        url: str,
        meta: DownloadMeta,
        output_dir: Path,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
    ) -> Path:
        """Download audio from *url* into *output_dir*.

        Returns the path to the downloaded file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = self.get_output_template(meta)
        base_path = output_dir / output_name

        expected_path = base_path.with_suffix(f".{self._settings.audio_format}")
        overwrite = self._settings.overwrite

        if expected_path.exists():
            if overwrite == "skip":
                logger.info("File already exists (skip): %s", expected_path)
                return expected_path
            elif overwrite == "metadata":
                logger.info("File exists, will update metadata only: %s", expected_path)
                return expected_path
            elif overwrite == "force":
                logger.info("Overwriting existing file: %s", expected_path)
                expected_path.unlink()

        base_path.parent.mkdir(parents=True, exist_ok=True)

        options = self.get_yt_dlp_options(base_path, progress_callback)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_yt_dlp, url, options)

            output_file = self._find_output_file(base_path)
            if not output_file:
                raise DownloadError(f"Output file not found: {base_path}")

            logger.info("Downloaded: %s", output_file)
            return output_file

        except DownloadError:
            raise
        except Exception as e:
            raise DownloadError(f"Download failed: {e}") from e

    @staticmethod
    def _run_yt_dlp(url: str, options: dict[str, Any]) -> None:
        import yt_dlp
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

    def _find_output_file(self, base_path: Path) -> Path | None:
        extensions = [
            self._settings.audio_format,
            "mp3", "m4a", "flac", "opus", "ogg", "wav",
            "webm", "mp4",
        ]
        for ext in extensions:
            path = base_path.with_suffix(f".{ext}")
            if path.exists():
                return path
        for path in base_path.parent.glob(f"{base_path.stem}.*"):
            if path.suffix.lower() in [f".{e}" for e in extensions]:
                return path
        return None

    # ── metadata embedding ──────────────────────────────────────────

    async def embed_metadata(self, file_path: Path, meta: DownloadMeta) -> None:
        """Embed metadata into audio file using mutagen."""
        if not self._settings.embed_metadata:
            return

        try:
            suffix = file_path.suffix.lower()
            if suffix == ".mp3":
                await self._embed_mp3_metadata(file_path, meta)
            elif suffix == ".m4a":
                await self._embed_m4a_metadata(file_path, meta)
            elif suffix == ".flac":
                await self._embed_flac_metadata(file_path, meta)
            elif suffix in (".opus", ".ogg"):
                await self._embed_ogg_metadata(file_path, meta)
            else:
                logger.warning("Unsupported format for metadata: %s", suffix)
        except Exception as e:
            logger.error("Failed to embed metadata: %s", e)

    async def _embed_mp3_metadata(self, file_path: Path, meta: DownloadMeta) -> None:
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import ID3NoHeaderError

        loop = asyncio.get_event_loop()
        sep = self._settings.id3_separator
        artists = meta.artists or [meta.artist]

        def _embed() -> None:
            try:
                audio = EasyID3(file_path)
            except ID3NoHeaderError:
                audio = EasyID3()
                audio.save(file_path)
                audio = EasyID3(file_path)

            audio["title"] = meta.title
            audio["artist"] = [sep.join(artists)] if sep != "/" else artists
            audio["albumartist"] = [meta.album_artist or meta.artist]
            audio["album"] = [meta.album] if meta.album else []
            audio["genre"] = meta.genres if meta.genres else []
            audio["date"] = [meta.date] if meta.date else (
                [str(meta.year)] if meta.year else []
            )
            audio["tracknumber"] = [str(meta.track_number)] if meta.track_number else []
            audio["discnumber"] = [str(meta.disc_number)] if meta.disc_number else []
            audio.save()

        await loop.run_in_executor(None, _embed)

        if self._settings.embed_cover and meta.cover_url:
            await self._embed_mp3_cover(file_path, meta.cover_url)

    async def _embed_mp3_cover(self, file_path: Path, cover_url: str) -> None:
        from mutagen.id3 import APIC, ID3

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = ID3(file_path)
            audio.delall("APIC")
            audio.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data))
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_m4a_metadata(self, file_path: Path, meta: DownloadMeta) -> None:
        from mutagen.mp4 import MP4

        loop = asyncio.get_event_loop()
        artists = meta.artists or [meta.artist]

        def _embed() -> None:
            audio = MP4(file_path)
            audio["\xa9nam"] = [meta.title]
            audio["\xa9ART"] = artists
            audio["aART"] = [meta.album_artist or meta.artist]
            audio["\xa9alb"] = [meta.album] if meta.album else []
            audio["\xa9gen"] = meta.genres if meta.genres else []
            audio["\xa9day"] = [meta.date] if meta.date else (
                [str(meta.year)] if meta.year else []
            )
            if meta.track_number is not None:
                audio["trkn"] = [(meta.track_number, meta.tracks_count or 0)]
            if meta.disc_number is not None:
                audio["disk"] = [(meta.disc_number, meta.disc_count or 0)]
            audio.save()

        await loop.run_in_executor(None, _embed)

        if self._settings.embed_cover and meta.cover_url:
            await self._embed_m4a_cover(file_path, meta.cover_url)

    async def _embed_m4a_cover(self, file_path: Path, cover_url: str) -> None:
        from mutagen.mp4 import MP4, MP4Cover

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = MP4(file_path)
            audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_flac_metadata(self, file_path: Path, meta: DownloadMeta) -> None:
        from mutagen.flac import FLAC

        loop = asyncio.get_event_loop()
        artists = meta.artists or [meta.artist]

        def _embed() -> None:
            audio = FLAC(file_path)
            audio["title"] = [meta.title]
            audio["artist"] = artists
            audio["albumartist"] = [meta.album_artist or meta.artist]
            audio["album"] = [meta.album] if meta.album else []
            audio["genre"] = meta.genres if meta.genres else []
            audio["date"] = [meta.date] if meta.date else (
                [str(meta.year)] if meta.year else []
            )
            audio["tracknumber"] = [str(meta.track_number)] if meta.track_number else []
            audio["discnumber"] = [str(meta.disc_number)] if meta.disc_number else []
            audio.save()

        await loop.run_in_executor(None, _embed)

        if self._settings.embed_cover and meta.cover_url:
            await self._embed_flac_cover(file_path, meta.cover_url)

    async def _embed_flac_cover(self, file_path: Path, cover_url: str) -> None:
        from mutagen.flac import FLAC, Picture

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = FLAC(file_path)
            audio.clear_pictures()
            picture = Picture()
            picture.type = 3
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_data
            audio.add_picture(picture)
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_ogg_metadata(self, file_path: Path, meta: DownloadMeta) -> None:
        from mutagen.oggopus import OggOpus
        from mutagen.oggvorbis import OggVorbis

        loop = asyncio.get_event_loop()
        suffix = file_path.suffix.lower()
        artists = meta.artists or [meta.artist]

        def _embed() -> None:
            audio = OggOpus(file_path) if suffix == ".opus" else OggVorbis(file_path)
            audio["title"] = [meta.title]
            audio["artist"] = artists
            audio["albumartist"] = [meta.album_artist or meta.artist]
            audio["album"] = [meta.album] if meta.album else []
            audio["genre"] = meta.genres if meta.genres else []
            audio["date"] = [meta.date] if meta.date else (
                [str(meta.year)] if meta.year else []
            )
            audio["tracknumber"] = [str(meta.track_number)] if meta.track_number else []
            audio["discnumber"] = [str(meta.disc_number)] if meta.disc_number else []
            audio.save()

        await loop.run_in_executor(None, _embed)

        if self._settings.embed_cover and meta.cover_url:
            await self._embed_ogg_cover(file_path, meta.cover_url)

    async def _embed_ogg_cover(self, file_path: Path, cover_url: str) -> None:
        from mutagen.flac import Picture
        from mutagen.oggopus import OggOpus
        from mutagen.oggvorbis import OggVorbis

        cover_data = await self._download_cover(cover_url)
        if not cover_data:
            return

        loop = asyncio.get_event_loop()
        suffix = file_path.suffix.lower()

        def _embed() -> None:
            picture = Picture()
            picture.type = 3
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover_data
            encoded_data = base64.b64encode(picture.write()).decode("ascii")

            audio = OggOpus(file_path) if suffix == ".opus" else OggVorbis(file_path)
            audio["metadata_block_picture"] = [encoded_data]
            audio.save()

        await loop.run_in_executor(None, _embed)

    # ── lyrics embedding ────────────────────────────────────────────

    async def embed_lyrics(self, file_path: Path, lyrics: str) -> None:
        if not self._settings.embed_lyrics or not lyrics:
            return

        suffix = file_path.suffix.lower()
        try:
            if suffix == ".mp3":
                await self._embed_mp3_lyrics(file_path, lyrics)
            elif suffix == ".m4a":
                await self._embed_m4a_lyrics(file_path, lyrics)
            elif suffix == ".flac":
                await self._embed_flac_lyrics(file_path, lyrics)
        except Exception as e:
            logger.warning("Failed to embed lyrics: %s", e)

    async def _embed_mp3_lyrics(self, file_path: Path, lyrics: str) -> None:
        from mutagen.id3 import ID3, USLT

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = ID3(file_path)
            audio.delall("USLT")
            audio.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics))
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_m4a_lyrics(self, file_path: Path, lyrics: str) -> None:
        from mutagen.mp4 import MP4

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = MP4(file_path)
            audio["\xa9lyr"] = [lyrics]
            audio.save()

        await loop.run_in_executor(None, _embed)

    async def _embed_flac_lyrics(self, file_path: Path, lyrics: str) -> None:
        from mutagen.flac import FLAC

        loop = asyncio.get_event_loop()

        def _embed() -> None:
            audio = FLAC(file_path)
            audio["lyrics"] = [lyrics]
            audio.save()

        await loop.run_in_executor(None, _embed)

    # ── cover download ──────────────────────────────────────────────

    async def _download_cover(self, cover_url: str) -> bytes | None:
        try:
            client = await self._get_http_client()
            response = await client.get(cover_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.warning("Failed to download cover: %s", e)
            return None


# ── helpers ─────────────────────────────────────────────────────────

def _format_speed(speed: float) -> str:
    if speed < 1024:
        return f"{speed:.0f} B/s"
    elif speed < 1024 * 1024:
        return f"{speed / 1024:.1f} KB/s"
    else:
        return f"{speed / (1024 * 1024):.1f} MB/s"


def _format_eta(eta: int) -> str:
    if eta < 60:
        return f"{eta}s"
    elif eta < 3600:
        return f"{eta // 60}m {eta % 60}s"
    else:
        return f"{eta // 3600}h {(eta % 3600) // 60}m"
