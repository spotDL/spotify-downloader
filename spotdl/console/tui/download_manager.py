"""
Concurrent download queue shared by the interactive interface.

Every job runs in its own thread with its own Downloader, because a Downloader
drives a single asyncio loop and a single ProgressHandler callback.
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field, replace
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from spotdl.console.save import save
from spotdl.console.sync import sync
from spotdl.console.tui.log_handler import BufferLogHandler
from spotdl.types.song import Song

logger = logging.getLogger(__name__)

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
ERROR = "error"
CANCELLED = "cancelled"

TERMINAL_STATUSES = {DONE, ERROR, CANCELLED}

_SKIP_MARKERS = ("skip",)
_ERROR_MARKERS = ("error", "failed")
_DONE_MARKERS = ("done", "complete", "finished")


def classify_status(status: str) -> str:
    """
    Map a tracker status to done, error, skip or active.

    ### Arguments
    - status: Raw status reported by the progress tracker.

    ### Returns
    - One of "done", "error", "skip" or "active".
    """

    value = (status or "").lower()
    if any(marker in value for marker in _SKIP_MARKERS):
        return "skip"
    if any(marker in value for marker in _ERROR_MARKERS):
        return ERROR
    if any(marker in value for marker in _DONE_MARKERS):
        return DONE
    return "active"


@dataclass
class DownloadJob:
    """
    One queued download operation.

    ### Attributes
    - id: Unique job identifier.
    - name: Name shown in the interface.
    - operation: "download", "save" or "sync".
    - songs: Songs handled by this job.
    - options: Options chosen in the interface.
    """

    id: str
    name: str
    operation: str
    songs: List[Song]
    options: Dict[str, Any]
    status: str = QUEUED
    progress: Dict[str, int] = field(default_factory=dict)
    song_status: Dict[str, str] = field(default_factory=dict)
    succeeded_urls: Set[str] = field(default_factory=set)
    skipped_urls: Set[str] = field(default_factory=set)
    failed_urls: Set[str] = field(default_factory=set)
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    cancel_requested: bool = False
    recorded: bool = False
    group_id: str = ""
    retry_of: Optional[str] = None
    m3u_template: Optional[str] = None
    m3u_songs: Optional[List[Song]] = None

    @property
    def total(self) -> int:
        """
        Number of songs in the job.
        """

        return len(self.songs)

    @property
    def done(self) -> int:
        """
        Number of songs that reached a final state.
        """

        return len(self.succeeded_urls | self.skipped_urls | self.failed_urls)

    @property
    def ok(self) -> int:
        """
        Number of songs downloaded.
        """

        return len(self.succeeded_urls)

    @property
    def errors(self) -> int:
        """
        Number of songs that failed.
        """

        return len(self.failed_urls)

    @property
    def skipped(self) -> int:
        """
        Number of songs skipped.
        """

        return len(self.skipped_urls)

    @property
    def percent(self) -> int:
        """
        Overall progress of the job, from 0 to 100.
        """

        if not self.songs:
            return 0
        terminal = self.succeeded_urls | self.skipped_urls | self.failed_urls
        total = 0
        for song in self.songs:
            if song.url in terminal:
                total += 100
            else:
                total += max(0, min(100, self.progress.get(song.url, 0)))
        return int(total / len(self.songs))

    def snapshot(self) -> Dict[str, Any]:
        """
        Build a plain dictionary for the interface.
        """

        return {
            "id": self.id,
            "name": self.name,
            "operation": self.operation,
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "percent": self.percent,
            "ok": self.ok,
            "errors": self.errors,
            "skipped": self.skipped,
            "failed": self.errors,
            "error": self.error,
            "can_retry": bool(self.failed_urls) and self.status in TERMINAL_STATUSES,
        }


class DownloadManager:
    """
    Runs download jobs in parallel up to a fixed limit.

    ### Attributes
    - max_parallel: Maximum number of jobs running at the same time.
    """

    def __init__(
        self,
        downloader_factory: Callable[[Dict[str, Any]], Any],
        max_parallel: int = 2,
        history_recorder: Optional[Callable[[DownloadJob], None]] = None,
    ) -> None:
        """
        Create the manager.

        ### Arguments
        - downloader_factory: Callable that builds a Downloader from options.
        - max_parallel: Maximum number of jobs running at the same time.
        - history_recorder: Optional callable invoked once per finished job.
        """

        self._factory = downloader_factory
        self._max_parallel = max(1, int(max_parallel))
        self._history_recorder = history_recorder
        self._jobs: Dict[str, DownloadJob] = {}
        self._order: List[str] = []
        self._queue: List[str] = []
        self._lock = threading.RLock()
        self._running = 0
        self._counter = 0

    @property
    def max_parallel(self) -> int:
        """
        Maximum number of jobs running at the same time.
        """

        return self._max_parallel

    def submit(
        self,
        name: str,
        operation: str,
        songs: List[Song],
        options: Dict[str, Any],
        group_id: Optional[str] = None,
        retry_of: Optional[str] = None,
        m3u_template: Optional[str] = None,
        m3u_songs: Optional[List[Song]] = None,
    ) -> str:
        """
        Add a job to the queue and start it when a slot is free.

        ### Arguments
        - name: Name shown in the interface.
        - operation: "download", "save" or "sync".
        - songs: Songs handled by the job.
        - options: Options chosen in the interface.
        - group_id: Identifier shared by the original job and its retries.
        - retry_of: Identifier of the job this one retries.
        - m3u_template: m3u file template kept when the engine write is skipped.
        - m3u_songs: Full song list used to rewrite the m3u after the job.

        ### Returns
        - The identifier of the new job.
        """

        with self._lock:
            self._counter += 1
            job_id = f"job-{self._counter}"
            job = DownloadJob(
                job_id,
                name,
                operation,
                list(songs),
                dict(options),
                group_id=group_id or job_id,
                retry_of=retry_of,
                m3u_template=m3u_template or options.get("m3u") or None,
                m3u_songs=list(m3u_songs) if m3u_songs else None,
            )
            self._jobs[job_id] = job
            self._order.append(job_id)
            self._queue.append(job_id)

        self._dispatch()
        return job_id

    def _dispatch(self) -> None:
        starts: List[DownloadJob] = []
        with self._lock:
            while self._running < self._max_parallel and self._queue:
                job_id = self._queue.pop(0)
                job = self._jobs[job_id]
                if job.status != QUEUED:
                    continue
                job.status = RUNNING
                self._running += 1
                starts.append(job)

        for job in starts:
            threading.Thread(
                target=self._run_job,
                args=(job,),
                name=f"spotdl-{job.id}",
                daemon=True,
            ).start()

    def _run_job(self, job: DownloadJob) -> None:
        spotdl_logger = logging.getLogger("spotdl")
        previous_level = spotdl_logger.level
        handler = BufferLogHandler(partial(self._on_log, job))
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        spotdl_logger.addHandler(handler)
        if spotdl_logger.getEffectiveLevel() > logging.INFO:
            spotdl_logger.setLevel(logging.INFO)

        try:
            downloader = self._factory(job.options)
            job.loop = downloader.loop
            asyncio.set_event_loop(downloader.loop)
            downloader.progress_handler.update_callback = (
                lambda tracker, message, job=job: self._on_progress(job, tracker)
            )
            downloader.progress_handler.set_songs(job.songs)

            if job.operation == "save":
                save(query=[song.url for song in job.songs], downloader=downloader)
            elif job.operation == "sync":
                sync(query=job.options["query"], downloader=downloader)
            else:
                results = downloader.download_multiple_songs(job.songs)
                self._reconcile(job, results)
        except asyncio.CancelledError:
            self._finish(job, CANCELLED)
            return
        except Exception as exc:
            logger.error("Download job %s failed: %s", job.id, exc)
            self._finish(job, ERROR, message=str(exc))
            return
        finally:
            spotdl_logger.removeHandler(handler)
            spotdl_logger.setLevel(previous_level)

        self._finish(job, DONE)

    def _reconcile(self, job: DownloadJob, results: Any) -> None:
        if not results:
            return
        with self._lock:
            for song, path in results:
                url = getattr(song, "url", None)
                if not url:
                    continue
                if (
                    path is None
                    and url not in job.skipped_urls
                    and url not in job.succeeded_urls
                ):
                    job.failed_urls.add(url)
                    job.song_status[url] = "error"

    def _on_log(self, job: DownloadJob, message: str) -> None:
        with self._lock:
            job.logs.append(message)
            if len(job.logs) > 2000:
                del job.logs[: len(job.logs) - 2000]

    def job_logs(self, job_id: str, start: int = 0) -> List[str]:
        """
        Get the log lines captured for a job.

        ### Arguments
        - job_id: Identifier returned by `submit`.
        - start: Index of the first line to return.

        ### Returns
        - The log lines from `start` to the end.
        """

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return []
            return job.logs[start:]

    def _finish(
        self, job: DownloadJob, status: str, message: Optional[str] = None
    ) -> None:
        record = False
        with self._lock:
            job.status = CANCELLED if job.cancel_requested else status
            job.error = message
            self._running = max(0, self._running - 1)
            if job.status in TERMINAL_STATUSES and not job.recorded:
                job.recorded = True
                record = True

        if record and self._history_recorder is not None:
            try:
                self._history_recorder(job)
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Could not record job history: %s", exc)

        if job.status != CANCELLED and job.m3u_template and job.m3u_songs:
            self._write_m3u(job)

        self._dispatch()

    def _on_progress(self, job: DownloadJob, tracker: Any) -> None:
        song = getattr(tracker, "song", None)
        url = getattr(song, "url", None)
        if not url:
            return

        progress = int(getattr(tracker, "progress", 0) or 0)
        status = str(getattr(tracker, "status", "") or "")

        with self._lock:
            if job.status in TERMINAL_STATUSES or job.cancel_requested:
                return

            job.progress[url] = max(0, min(100, progress))
            job.song_status[url] = status

            kind = classify_status(status)
            if kind == "active":
                return

            if kind == DONE:
                job.failed_urls.discard(url)
                job.skipped_urls.discard(url)
                job.succeeded_urls.add(url)
            elif kind == "skip":
                job.failed_urls.discard(url)
                job.succeeded_urls.discard(url)
                job.skipped_urls.add(url)
            else:
                if url not in job.succeeded_urls and url not in job.skipped_urls:
                    job.failed_urls.add(url)

    def failed_songs(self, job_id: str) -> List[Song]:
        """
        List the songs of a job that failed.

        ### Arguments
        - job_id: Identifier returned by `submit`.
        """

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return []
            return [song for song in job.songs if song.url in job.failed_urls]

    def retry_failed(
        self, job_id: str, links: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Queue a new job with only the songs that failed.

        ### Arguments
        - job_id: Identifier of the finished job.
        - links: Optional download link chosen by the user per song url.

        ### Returns
        - The identifier of the new job, or None when there is nothing to retry.
        """

        with self._lock:
            job = self._jobs.get(job_id)
            if (
                job is None
                or not job.failed_urls
                or job.status not in TERMINAL_STATUSES
            ):
                return None

            failed = [
                (
                    replace(song, download_url=links[song.url])
                    if links and links.get(song.url)
                    else song
                )
                for song in job.songs
                if song.url in job.failed_urls
            ]
            if not failed:
                return None

            options = dict(job.options)
            options["m3u"] = None
            options["save_file"] = None
            operation = job.operation
            name = job.name
            group_id = job.group_id
            retry_of = job.id
            m3u_template = job.m3u_template
            m3u_songs = job.m3u_songs or list(job.songs)

        return self.submit(
            name,
            operation,
            failed,
            options,
            group_id=group_id,
            retry_of=retry_of,
            m3u_template=m3u_template,
            m3u_songs=m3u_songs,
        )

    def _write_m3u(self, job: DownloadJob) -> None:
        template = job.m3u_template
        songs = job.m3u_songs or []
        if not template or not songs:
            return

        try:
            # pylint: disable=import-outside-toplevel
            from spotdl.console.tui.library import present_songs
            from spotdl.console.tui.settings import build_downloader_settings
            from spotdl.utils.m3u import gen_m3u_files

            settings = build_downloader_settings(dict(job.options))
            existing = present_songs(songs, settings)
            if not existing:
                return

            gen_m3u_files(
                existing,
                template,
                settings["output"],
                settings["format"],
                settings["restrict"],
                False,
                settings["detect_formats"],
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Could not write m3u: %s", exc)

    def snapshot(self) -> List[Dict[str, Any]]:
        """
        List every job in submission order.
        """

        with self._lock:
            return [self._jobs[job_id].snapshot() for job_id in self._order]

    def song_progress(self, job_id: str) -> Dict[str, Tuple[int, str, bool]]:
        """
        Get the progress of every song in a job.

        ### Arguments
        - job_id: Identifier returned by `submit`.

        ### Returns
        - Mapping of song url to (progress, status, completed).
        """

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {}
            terminal = job.succeeded_urls | job.skipped_urls | job.failed_urls
            return {
                song.url: (
                    job.progress.get(song.url, 0),
                    job.song_status.get(song.url, ""),
                    song.url in terminal,
                )
                for song in job.songs
            }

    def job_options(
        self, job_id: str
    ) -> Optional[Tuple[str, str, List[Song], Dict[str, Any]]]:
        """
        Get the data needed to reopen a job in the download screen.

        ### Arguments
        - job_id: Identifier returned by `submit`.

        ### Returns
        - (name, operation, songs, options) or None when the job is unknown.
        """

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return job.name, job.operation, list(job.songs), dict(job.options)

    def active_count(self) -> int:
        """
        Number of jobs queued or running.
        """

        with self._lock:
            return sum(
                1 for job in self._jobs.values() if job.status in (QUEUED, RUNNING)
            )

    def aggregate(self) -> Tuple[int, int]:
        """
        Count active jobs and their weighted progress.

        ### Returns
        - (active job count, aggregate percent).
        """

        with self._lock:
            active = [
                job for job in self._jobs.values() if job.status in (QUEUED, RUNNING)
            ]
            if not active:
                return 0, 0
            total_songs = sum(len(job.songs) for job in active)
            percent = sum(job.percent * len(job.songs) for job in active)
            return len(active), int(percent / max(1, total_songs))

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a queued or running job.

        ### Arguments
        - job_id: Identifier returned by `submit`.

        ### Returns
        - True when the job was cancelled, False otherwise.
        """

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if job.status == QUEUED:
                job.cancel_requested = True
                job.status = CANCELLED
                if job_id in self._queue:
                    self._queue.remove(job_id)
                return True

            if job.status != RUNNING:
                return False

            job.cancel_requested = True
            loop = job.loop

        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(
                lambda: [task.cancel() for task in asyncio.all_tasks(loop)]
            )
        return True

    def clear_finished(self) -> None:
        """
        Remove every job that already finished.
        """

        with self._lock:
            self._order = [
                job_id
                for job_id in self._order
                if self._jobs[job_id].status not in TERMINAL_STATUSES
            ]
            for job_id in list(self._jobs):
                if self._jobs[job_id].status in TERMINAL_STATUSES:
                    del self._jobs[job_id]
