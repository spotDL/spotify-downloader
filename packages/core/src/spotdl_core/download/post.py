"""Post-processing for the download pipeline: ``.lrc`` generation, m3u playlist
building, archive updates, and SponsorBlock chapter removal.

Ports v4's ``spotdl/utils/lrc.py`` (``generate_lrc``), ``spotdl/utils/m3u.py``
(``create_m3u_content`` / ``gen_m3u_files`` with ``{list}`` / ``{list[..]}``
templating and ``detect_formats``), the archive-add rule from
``spotdl/download/downloader.py``, and the SponsorBlock post-processor block
(``SponsorBlockPP`` / ``ModifyChaptersPP``) against the v5 domain model.

The ``{list}`` templating semantics and :data:`SPONSOR_BLOCK_CATEGORIES` are a
CONTRACT (feature parity). The synced-lyrics search and the SponsorBlock
post-processors are reached only through injectable seams, so the default suite
is fully offline: ``syncedlyrics`` need not be installed and yt-dlp's
post-processors are never invoked. Both are lazily imported so their absence only
disables the corresponding feature.

The m3u helpers operate over **many** tracks, so they are module-level utilities
the orchestrator (Plan 7) calls around per-track ``download()`` runs — not
per-track pipeline steps. Path rendering reuses ``paths.build_output_path`` /
``paths.render_template`` so templating stays single-sourced.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from spotdl_core.download.context import (
    DownloadConfig,
    DownloadContext,
    DownloadRequest,
    OutputFormat,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
    RestrictMode,
)
from spotdl_core.download.paths import build_output_path, render_template, sanitize_string
from spotdl_core.download.tags import LRC_REGEX
from spotdl_core.model import AudioCandidate, Lyrics, LyricsKind, ProviderId, Track
from spotdl_core.providers.errors import PostProcessingFailed

__all__ = [
    "SPONSOR_BLOCK_CATEGORIES",
    "M3uEntry",
    "SponsorBlock",
    "SponsorBlockStep",
    "SyncedLyricsLibrary",
    "SyncedLyricsSearch",
    "YtDlpSponsorBlock",
    "archive_update",
    "create_m3u_content",
    "gen_m3u_files",
    "generate_lrc",
]

logger = logging.getLogger(__name__)

# CONTRACT: the eight v4 SponsorBlock categories (key -> human label), ported
# verbatim from ``spotdl/download/downloader.py``. Passed to yt-dlp's
# ``SponsorBlockPP`` / ``ModifyChaptersPP`` as the set of segments to strip.
SPONSOR_BLOCK_CATEGORIES: dict[str, str] = {
    "sponsor": "Sponsor",
    "intro": "Intermission/Intro Animation",
    "outro": "Endcards/Credits",
    "selfpromo": "Unpaid/Self Promotion",
    "preview": "Preview/Recap",
    "filler": "Filler Tangent",
    "interaction": "Interaction Reminder",
    "music_offtopic": "Non-Music Section",
}

# EXTINF metadata line template (v4 ``create_m3u_content``): duration in seconds
# plus an ``album-artist - title`` label. Carries no ``{output-ext}`` token.
_EXTINF_TEMPLATE = "#EXTINF:{duration},{album-artist} - {title}"


# --- lrc ------------------------------------------------------------------


@runtime_checkable
class SyncedLyricsSearch(Protocol):
    """Seam over a synced-lyrics provider. Returns LRC text or ``None``."""

    def search(self, query: str) -> str | None: ...


class SyncedLyricsLibrary:
    """Default :class:`SyncedLyricsSearch` backed by the optional ``syncedlyrics``
    package (the ``lrc`` extra). The import is deferred to call time; if the extra
    is not installed — or a lookup fails — :meth:`search` returns ``None`` so a
    missing dependency only disables ``.lrc`` generation."""

    def search(self, query: str) -> str | None:
        try:
            import syncedlyrics
        except ImportError:
            return None
        try:
            result = syncedlyrics.search(query)
        except Exception:
            return None
        return str(result) if result else None


def _display_name(track: Track) -> str:
    """``"<main-artist> - <title>"`` search query (port of v4 ``Song.display_name``)."""
    return f"{track.main_artist} - {track.name}"


def _is_synced(lyrics: Lyrics) -> bool:
    """Whether request lyrics already carry synced/translation content worth
    saving directly (v4 preferred ``song.lyrics`` when ``has_translation``).

    ``Lyrics.kind`` is a hint; the ``LRC`` timestamp regex is authoritative
    (mirrors the tag module's plain-vs-synced detection)."""
    if lyrics.kind is LyricsKind.SYNCED:
        return True
    return any(line and LRC_REGEX.match(line) for line in lyrics.text.splitlines()[:5])


def generate_lrc(
    request: DownloadRequest, output_file: Path, search: SyncedLyricsSearch
) -> Path | None:
    """Write a ``<output>.lrc`` sidecar for ``request`` (port of v4
    ``lrc.generate_lrc``).

    Prefers the request's own lyrics when they are synced; otherwise falls back
    to the injected ``search`` seam (offline in tests). Returns the written
    ``.lrc`` path, or ``None`` when no synced lyrics are available. A search
    failure is swallowed (best-effort, matches v4).
    """
    lrc_data: str | None = None
    if request.lyrics is not None and _is_synced(request.lyrics):
        lrc_data = request.lyrics.text
    else:
        try:
            lrc_data = search.search(_display_name(request.track))
        except Exception:
            lrc_data = None

    if not lrc_data:
        logger.debug("No lrc data for %s", _display_name(request.track))
        return None

    lrc_path = output_file.with_suffix(".lrc")
    lrc_path.write_text(lrc_data, encoding="utf-8")
    logger.debug("Saved lrc file %s", lrc_path)
    return lrc_path


# --- m3u ------------------------------------------------------------------


class M3uEntry(BaseModel):
    """One playlist row: the downloaded ``track``, its real ``path`` (used for
    ``detect_formats`` existence checks), and the optional ``list_name`` used to
    group tracks into per-playlist m3u files."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    track: Track
    path: Path
    list_name: str | None = None


def _m3u_request(
    track: Track,
    list_name: str | None,
    template: str,
    output_format: OutputFormat,
    restrict: RestrictMode,
) -> DownloadRequest:
    """Build the minimal :class:`DownloadRequest` needed to render an m3u path.

    Only ``track`` / ``output_template`` / ``output_format`` / ``restrict`` /
    ``list_name`` participate in path rendering; the candidate is a rendering-only
    placeholder (``render_template`` never reads it)."""
    return DownloadRequest(
        track=track,
        candidate=AudioCandidate(
            provider=track.provider or ProviderId.YOUTUBE,
            provider_id=track.provider_id or "m3u",
            url="",
            name=track.name,
        ),
        output_template=template,
        output_format=output_format,
        restrict=restrict,
        list_name=list_name,
    )


def _rendered_relative_path(
    track: Track,
    list_name: str | None,
    template: str,
    output_format: OutputFormat,
    restrict: RestrictMode,
) -> Path:
    """Render the template to a **relative** path (no output dir baked in) by
    running ``build_output_path`` against a ``.``-rooted config."""
    request = _m3u_request(track, list_name, template, output_format, restrict)
    config = DownloadConfig(output_dir=Path("."), temp_dir=Path("."))
    return build_output_path(request, config)


def create_m3u_content(
    entries: Iterable[M3uEntry],
    template: str,
    output_format: OutputFormat,
    *,
    restrict: RestrictMode = RestrictMode.NONE,
    detect_formats: tuple[OutputFormat, ...] = (),
) -> str:
    """Build m3u8 text for ``entries`` (port of v4 ``create_m3u_content``).

    Emits the ``#EXTM3U`` header, then per track an ``#EXTINF`` metadata line and
    the rendered relative audio path. When ``detect_formats`` is given, the first
    format whose file already exists on disk (checked against the entry's real
    ``path``) supplies the extension; otherwise ``output_format`` is used.
    """
    lines = ["#EXTM3U"]

    for entry in entries:
        request = _m3u_request(entry.track, entry.list_name, template, output_format, restrict)
        lines.append(render_template(entry.track, request, _EXTINF_TEMPLATE, output_ext=""))

        chosen = output_format
        for fmt in detect_formats:
            if entry.path.with_suffix(f".{fmt.value}").exists():
                chosen = fmt
                break

        rendered = _rendered_relative_path(entry.track, entry.list_name, template, chosen, restrict)
        lines.append(str(rendered))

    return "\n".join(lines) + "\n"


def gen_m3u_files(
    entries: Iterable[M3uEntry],
    file_name: str | None,
    template: str,
    output_format: OutputFormat,
    *,
    restrict: RestrictMode = RestrictMode.NONE,
    detect_formats: tuple[OutputFormat, ...] = (),
) -> list[Path]:
    """Write one or more m3u8 files for ``entries`` (port of v4 ``gen_m3u_files``).

    ``file_name`` templating (v4 parity):

    - ``None`` -> ``"{list[0]}.m3u8"`` (name after the first playlist).
    - trailing slash -> append ``"{list[0]}.m3u8"``.
    - no ``.m3u``/``.m3u8`` suffix -> append ``.m3u8``.
    - contains ``{list}`` -> one file per distinct ``list_name``.
    - contains ``{list[...]}`` -> a single file spanning all tracks.
    - otherwise -> the literal name, spanning all tracks.

    A ``{list``-containing name with no playlists logs a warning and writes
    nothing. Returns the paths actually written.
    """
    entries = list(entries)

    if not file_name:
        file_name = "{list[0]}.m3u8"
    if file_name.endswith("/") or file_name.endswith("\\"):
        file_name += "{list[0]}.m3u8"
    if not file_name.endswith(".m3u") and not file_name.endswith(".m3u8"):
        file_name += ".m3u8"

    lists: dict[str, list[M3uEntry]] = {}
    for entry in entries:
        if entry.list_name is None:
            continue
        lists.setdefault(entry.list_name, []).append(entry)

    if not lists and "{list" in file_name:
        logger.warning(
            "M3U file name contains '{list}' but no playlists were provided. "
            "Specify a concrete filename."
        )
        return []

    written: list[Path] = []
    if "{list}" in file_name:
        for list_name, sublist in lists.items():
            written.append(
                _write_m3u_file(
                    file_name.format(list=list_name),
                    sublist,
                    template,
                    output_format,
                    restrict,
                    detect_formats,
                )
            )
    elif "{list[" in file_name and "]}" in file_name:
        written.append(
            _write_m3u_file(
                file_name.format(list=list(lists.keys())),
                entries,
                template,
                output_format,
                restrict,
                detect_formats,
            )
        )
    else:
        written.append(
            _write_m3u_file(file_name, entries, template, output_format, restrict, detect_formats)
        )

    return written


def _write_m3u_file(
    file_name: str,
    entries: list[M3uEntry],
    template: str,
    output_format: OutputFormat,
    restrict: RestrictMode,
    detect_formats: tuple[OutputFormat, ...],
) -> Path:
    """Render and write a single m3u8 file, returning its absolute path (port of
    v4 ``create_m3u_file``: each path part is sanitized)."""
    content = create_m3u_content(
        entries, template, output_format, restrict=restrict, detect_formats=detect_formats
    )
    file_path = Path(*(sanitize_string(part) for part in Path(file_name).parts)).absolute()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


# --- archive --------------------------------------------------------------


def archive_update(
    current: frozenset[str],
    results: Iterable[tuple[str, bool]],
    *,
    add_unavailable: bool,
) -> frozenset[str]:
    """Return ``current`` extended with the URLs of successful downloads (port of
    the v4 archive-add rule). When ``add_unavailable`` is set, failed URLs are
    recorded too. ``results`` is an iterable of ``(url, succeeded)`` pairs."""
    urls = set(current)
    for url, succeeded in results:
        if succeeded or add_unavailable:
            urls.add(url)
    return frozenset(urls)


# --- sponsorblock ---------------------------------------------------------


@runtime_checkable
class SponsorBlock(Protocol):
    """Seam over SponsorBlock chapter removal. Given the raw yt-dlp info dict and
    the audio path, returns the (possibly rewritten) audio path."""

    def process(self, info: dict[str, Any], audio_path: Path) -> Path: ...


class YtDlpSponsorBlock:
    """Default :class:`SponsorBlock` backed by yt-dlp's ``SponsorBlockPP`` /
    ``ModifyChaptersPP`` (lazily imported).

    Raises :class:`ImportError` when the post-processors are unavailable so the
    step can degrade gracefully; any other failure propagates to be wrapped as
    :class:`PostProcessingFailed`.
    """

    def __init__(self, categories: dict[str, str] | None = None) -> None:
        self._categories = categories or SPONSOR_BLOCK_CATEGORIES

    def process(self, info: dict[str, Any], audio_path: Path) -> Path:
        from yt_dlp import YoutubeDL  # type: ignore[import-untyped]
        from yt_dlp.postprocessor.modify_chapters import (  # type: ignore[import-untyped]
            ModifyChaptersPP,
        )
        from yt_dlp.postprocessor.sponsorblock import (  # type: ignore[import-untyped]
            SponsorBlockPP,
        )

        ydl = YoutubeDL({"quiet": True, "no_warnings": True})
        info = dict(info)
        info["filepath"] = str(audio_path)

        _, info = SponsorBlockPP(ydl, list(self._categories)).run(info)
        chapters = info.get("sponsorblock_chapters") or []
        if chapters:
            logger.info("Removing %d sponsor segment(s) from %s", len(chapters), audio_path.name)
            modify = ModifyChaptersPP(ydl, remove_sponsor_segments=list(self._categories))
            files_to_delete, info = modify.run(info)
            for file_to_delete in files_to_delete:
                with contextlib.suppress(OSError):
                    Path(file_to_delete).unlink()

        return Path(info.get("filepath", str(audio_path)))


class SponsorBlockStep:
    """Pipeline step that strips SponsorBlock segments from ``ctx.final_path`` off
    the event loop, swapping in the rewritten path.

    When the yt-dlp post-processors are unavailable (``ImportError``) the step
    degrades to a no-op rather than failing the download; any genuine
    SponsorBlock error is wrapped as :class:`PostProcessingFailed`.
    """

    def __init__(
        self, sponsor_block: SponsorBlock, on_progress: ProgressCallback | None = None
    ) -> None:
        self._sponsor_block = sponsor_block
        self._on_progress = on_progress

    async def __call__(self, ctx: DownloadContext) -> DownloadContext:
        self._emit(ProgressEvent(phase=ProgressPhase.POST))
        audio_path = ctx.final_path
        if audio_path is None:
            raise PostProcessingFailed("no audio file to run SponsorBlock on")

        info = ctx.source_info or {}
        try:
            new_path = await asyncio.to_thread(self._sponsor_block.process, info, audio_path)
        except ImportError:
            # yt-dlp post-processors are unavailable -> degrade to a no-op.
            logger.debug("SponsorBlock post-processors unavailable; skipping")
            return ctx
        except PostProcessingFailed:
            raise
        except Exception as exc:  # noqa: BLE001 - any genuine failure is a post error
            raise PostProcessingFailed(f"SponsorBlock failed: {exc}") from exc

        if new_path == audio_path:
            return ctx
        return ctx.updated(final_path=new_path)

    def _emit(self, event: ProgressEvent) -> None:
        if self._on_progress is None:
            return
        # progress is best-effort: a raising callback must never abort the step
        with contextlib.suppress(Exception):
            self._on_progress(event)
