"""
Threaded backend for the spotDL GUI.

The GUI never talks to the download engine directly. Instead it submits jobs to
a single long-lived worker thread that owns the Spotify client and the asyncio
event loop (spotDL binds its event loop to the thread that creates the
``Downloader``). Progress and results are reported back through a callback that
the GUI marshals onto the GTK main loop with ``GLib.idle_add``.
"""

import logging
import queue
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, cast

if TYPE_CHECKING:
    from spotdl.download.downloader import Downloader
    from spotdl.types.options import DownloaderOptionalOptions

logger = logging.getLogger(__name__)

__all__ = [
    "DownloadManager",
    "EVENT_STATUS",
    "EVENT_SEARCH_DONE",
    "EVENT_PROGRESS",
    "EVENT_SONG_DONE",
    "EVENT_JOB_DONE",
    "EVENT_ERROR",
]

# Event types passed to the ``on_event`` callback.
EVENT_STATUS = "status"  # coarse phase update shown on the loading screen
EVENT_SEARCH_DONE = "search-done"
EVENT_PROGRESS = "progress"
EVENT_SONG_DONE = "song-done"
EVENT_JOB_DONE = "job-done"
EVENT_ERROR = "error"

EventCallback = Callable[[str, Dict[str, Any]], None]

_Job = Tuple[List[str], Dict[str, Any], EventCallback, bool]

# Settings keys that require rebuilding the Downloader when they change.
_DOWNLOADER_KEYS = ("output", "format", "bitrate", "threads", "generate_lrc")

# When a song fails on the default source (YouTube Music), we re-attempt it from
# these alternative sources, in order, until one works. Plain YouTube often has a
# downloadable video when the music.youtube.com URL is blocked, and SoundCloud /
# Bandcamp are entirely different sources (not yt-dlp/YouTube).
_FALLBACK_PROVIDER_SETS = (["youtube"], ["soundcloud"], ["bandcamp"])

_PROVIDER_LABELS = {
    "youtube": "YouTube",
    "youtube-music": "YouTube Music",
    "soundcloud": "SoundCloud",
    "bandcamp": "Bandcamp",
    "piped": "Piped",
}


class DownloadManager:
    """
    Runs spotDL download jobs on a dedicated background thread.
    """

    def __init__(self, spotify_options: Optional[Dict[str, Any]] = None) -> None:
        """
        ### Arguments
        - spotify_options: Optional overrides for the Spotify client. When
          omitted, spotDL's bundled default credentials are used.
        """

        self._queue: "queue.Queue[Optional[_Job]]" = queue.Queue()
        self._spotify_options = spotify_options or {}
        self._spotify_ready = False
        self._downloader: Optional["Downloader"] = None
        self._downloader_key: Optional[Tuple[Any, ...]] = None
        self._thread = threading.Thread(
            target=self._worker, name="spotdl-gui-worker", daemon=True
        )
        self._thread.start()

    def submit(
        self,
        query: List[str],
        downloader_settings: Dict[str, Any],
        on_event: EventCallback,
        fallback: bool = True,
    ) -> None:
        """
        Queue a download job.

        ### Arguments
        - query: List of Spotify URLs and/or free-text search terms.
        - downloader_settings: ``DownloaderOptions``-compatible settings dict.
        - on_event: Callback invoked (from the worker thread) with
          ``(event_type, payload)``.
        - fallback: When ``True``, failed songs are re-attempted from
          alternative audio sources before being reported as failed.
        """

        self._queue.put((query, downloader_settings, on_event, fallback))

    def shutdown(self) -> None:
        """Signal the worker thread to stop after finishing the current job."""

        self._queue.put(None)

    def _ensure_spotify(self, on_event: EventCallback) -> None:
        """Initialize the global Spotify client exactly once."""

        if self._spotify_ready:
            return

        on_event(EVENT_STATUS, {"message": "Connecting to Spotify\u2026"})

        # Imported lazily so importing this module never pulls in the whole
        # download stack until a job actually runs.
        # pylint: disable=import-outside-toplevel
        from spotdl.utils.config import SPOTIFY_OPTIONS
        from spotdl.utils.spotify import SpotifyClient

        options = {**SPOTIFY_OPTIONS, **self._spotify_options}
        SpotifyClient.init(
            client_id=options["client_id"],
            client_secret=options["client_secret"],
            user_auth=options["user_auth"],
            cache_path=options["cache_path"],
            no_cache=options["no_cache"],
            headless=options["headless"],
            use_official_api=options["use_official_api"],
        )
        self._spotify_ready = True

    def _get_downloader(
        self, settings: Dict[str, Any], on_event: EventCallback
    ) -> "Downloader":
        """
        Return a Downloader for ``settings``, reusing the cached instance when
        the relevant settings are unchanged (providers are expensive to set up).
        """

        # pylint: disable=import-outside-toplevel
        from spotdl.download.downloader import Downloader

        key = tuple(settings.get(name) for name in _DOWNLOADER_KEYS)
        if self._downloader is None or key != self._downloader_key:
            on_event(EVENT_STATUS, {"message": "Preparing download\u2026"})
            self._downloader = Downloader(
                settings=cast("DownloaderOptionalOptions", settings)
            )
            self._downloader_key = key

        return self._downloader

    def _worker(self) -> None:
        """Main loop for the background worker thread."""

        while True:
            job = self._queue.get()
            if job is None:
                self._queue.task_done()
                break

            query, settings, on_event, fallback = job
            try:
                self._run_job(query, settings, on_event, fallback)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Download job failed")
                message = str(exc).strip() or exc.__class__.__name__
                on_event(EVENT_ERROR, {"message": message})
            finally:
                self._queue.task_done()

    def _make_progress_cb(
        self, on_event: EventCallback, last_sent: Dict[str, Tuple[int, str]]
    ) -> Callable[[Any, str], None]:
        """Build a throttled progress callback bound to ``on_event``."""

        def progress_cb(tracker: Any, message: str) -> None:
            song = tracker.song
            progress = int(tracker.progress)
            previous = last_sent.get(song.url)
            if previous == (progress, message):
                return
            last_sent[song.url] = (progress, message)
            on_event(
                EVENT_PROGRESS,
                {
                    "url": song.url,
                    "name": tracker.song_name,
                    "progress": progress,
                    "message": message,
                },
            )

        return progress_cb

    def _run_job(
        self,
        query: List[str],
        settings: Dict[str, Any],
        on_event: EventCallback,
        fallback: bool = True,
    ) -> None:
        """Execute a single search + download job on the worker thread."""

        # pylint: disable=import-outside-toplevel
        from spotdl.download.progress_handler import ProgressHandler
        from spotdl.utils.search import parse_query

        self._ensure_spotify(on_event)

        downloader = self._get_downloader(settings, on_event)

        # Reset per-job engine state (the Downloader is reused between jobs).
        downloader.errors.clear()

        last_sent: Dict[str, Tuple[int, str]] = {}
        progress_cb = self._make_progress_cb(on_event, last_sent)

        downloader.progress_handler = ProgressHandler(
            simple_tui=True, update_callback=progress_cb, web_ui=True
        )

        on_event(EVENT_STATUS, {"message": "Searching for songs\u2026"})
        songs = parse_query(
            query=query,
            threads=downloader.settings["threads"],
            use_ytm_data=downloader.settings["ytm_data"],
            playlist_numbering=downloader.settings["playlist_numbering"],
            album_type=downloader.settings["album_type"],
            playlist_retain_track_cover=downloader.settings[
                "playlist_retain_track_cover"
            ],
        )

        if not songs:
            on_event(
                EVENT_ERROR,
                {"message": "No songs found. Check the link or search terms."},
            )
            return

        on_event(
            EVENT_SEARCH_DONE,
            {"songs": [{"url": song.url, "name": song.display_name} for song in songs]},
        )

        results = downloader.download_multiple_songs(songs)

        song_by_url = {song.url: song for song, _ in results}
        final: Dict[str, Optional[Any]] = {song.url: path for song, path in results}
        errors_map = _parse_errors(downloader.errors)

        # Backup plan: retry the songs that failed to download from other sources.
        if fallback:
            failed = [
                song_by_url[url]
                for url, path in final.items()
                if path is None and url in errors_map
            ]
            if failed:
                self._download_with_fallback(
                    failed, settings, progress_cb, on_event, last_sent, final
                )

        downloaded = 0
        for url, song in song_by_url.items():
            path = final[url]
            success = path is not None
            if success:
                downloaded += 1
            on_event(
                EVENT_SONG_DONE,
                {
                    "url": url,
                    "name": song.display_name,
                    "artist": getattr(song, "artist", "") or "",
                    "album": getattr(song, "album_name", "") or "",
                    "path": str(path) if path else None,
                    "error": None if success else errors_map.get(url),
                },
            )

        on_event(
            EVENT_JOB_DONE,
            {
                "downloaded": downloaded,
                "total": len(songs),
                "output_dir": _base_output_dir(settings["output"]),
            },
        )

    def _download_with_fallback(
        self,
        failed_songs: List[Any],
        settings: Dict[str, Any],
        progress_cb: Callable[[Any, str], None],
        on_event: EventCallback,
        last_sent: Dict[str, Tuple[int, str]],
        final: Dict[str, Optional[Any]],
    ) -> None:
        """
        Re-attempt ``failed_songs`` from alternative audio sources, updating
        ``final`` in place with any that succeed.
        """

        # pylint: disable=import-outside-toplevel
        from spotdl.download.downloader import Downloader
        from spotdl.download.progress_handler import ProgressHandler

        remaining = list(failed_songs)
        for providers in _FALLBACK_PROVIDER_SETS:
            if not remaining:
                break

            label = _PROVIDER_LABELS.get(providers[0], providers[0])
            for song in remaining:
                last_sent.pop(song.url, None)
                on_event(
                    EVENT_PROGRESS,
                    {
                        "url": song.url,
                        "name": song.display_name,
                        "progress": 0,
                        "message": f"Trying {label}\u2026",
                    },
                )

            fb_settings = {**settings, "audio_providers": list(providers)}
            try:
                fb_downloader = Downloader(
                    settings=cast("DownloaderOptionalOptions", fb_settings)
                )
                fb_downloader.progress_handler = ProgressHandler(
                    simple_tui=True, update_callback=progress_cb, web_ui=True
                )
                fb_results = fb_downloader.download_multiple_songs(remaining)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Fallback via %s failed", label)
                continue

            still_failed = []
            for song, path in fb_results:
                if path is not None:
                    logger.info("Recovered '%s' via %s", song.display_name, label)
                    final[song.url] = path
                else:
                    still_failed.append(song)
            remaining = still_failed


def _parse_errors(errors: List[str]) -> Dict[str, str]:
    """
    Build a ``{song_url: reason}`` map from the Downloader's error list.

    Engine errors are formatted as ``"{url} - {ClassName}: {message}"`` (see
    ``Downloader.search_and_download``).
    """

    mapping: Dict[str, str] = {}
    for error in errors:
        url, sep, reason = error.partition(" - ")
        if sep and url.startswith("http"):
            mapping[url] = reason.strip()
    return mapping


def _base_output_dir(output_template: str) -> str:
    """
    Return the base output directory from an output template, stripping any
    templated subfolders (e.g. ``.../Music/{album-artist}/{album}/...`` becomes
    ``.../Music``).
    """

    path = Path(output_template)
    base_parts: List[str] = []
    for part in path.parts:
        if "{" in part:
            break
        base_parts.append(part)

    return str(Path(*base_parts)) if base_parts else str(path.parent)
