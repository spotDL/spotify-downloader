import asyncio
import threading
import time
from types import SimpleNamespace

import pytest

from spotdl.console.tui.download_manager import (
    CANCELLED,
    DONE,
    ERROR,
    QUEUED,
    RUNNING,
    DownloadJob,
    DownloadManager,
    classify_status,
)


class FakeProgressHandler:
    def __init__(self):
        self.update_callback = None
        self.songs = []

    def set_songs(self, songs):
        self.songs = list(songs)


class FakeDownloader:
    instances = []
    gate = threading.Event()
    finish_immediately = True
    fail_urls = set()

    def __init__(self, settings=None):
        self.loop = asyncio.new_event_loop()
        self.progress_handler = FakeProgressHandler()
        FakeDownloader.instances.append(self)

    def download_multiple_songs(self, songs):
        for song in songs:
            tracker = SimpleNamespace(song=song, progress=40, status="downloading")
            self.progress_handler.update_callback(tracker, None)
        if not FakeDownloader.finish_immediately:
            FakeDownloader.gate.wait(5)
        for song in songs:
            status = "error" if song.url in FakeDownloader.fail_urls else "done"
            tracker = SimpleNamespace(song=song, progress=100, status=status)
            self.progress_handler.update_callback(tracker, None)


def _song(index):
    return SimpleNamespace(
        url=f"https://example.com/track/{index}",
        display_name=f"Song {index}",
        album_name="Album",
    )


def _wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


@pytest.fixture(autouse=True)
def _reset_fake():
    FakeDownloader.instances = []
    FakeDownloader.gate = threading.Event()
    FakeDownloader.finish_immediately = True
    FakeDownloader.fail_urls = set()
    yield


def test_classify_status():
    assert classify_status("Searching") == "active"
    assert classify_status("Downloading") == "active"
    assert classify_status("Done") == DONE
    assert classify_status("Skipped") == "skip"
    assert classify_status("Error") == ERROR


def test_manager_limits_parallel_jobs():
    FakeDownloader.finish_immediately = False
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=2)

    jobs = [
        manager.submit(f"job {index}", "download", [_song(index)], {})
        for index in range(3)
    ]

    assert _wait_until(lambda: len(FakeDownloader.instances) == 2)
    snapshot = {item["id"]: item for item in manager.snapshot()}
    assert snapshot[jobs[0]]["status"] == RUNNING
    assert snapshot[jobs[1]]["status"] == RUNNING
    assert snapshot[jobs[2]]["status"] == QUEUED

    FakeDownloader.gate.set()
    assert _wait_until(
        lambda: all(item["status"] == DONE for item in manager.snapshot())
    )
    assert len(FakeDownloader.instances) == 3


def test_manager_counts_each_song_once():
    manager = DownloadManager(lambda options: None)
    song = _song(0)
    job = DownloadJob("job", "name", "download", [song], {})
    tracker = SimpleNamespace(song=song, progress=100, status="done")

    manager._on_progress(job, tracker)
    manager._on_progress(job, tracker)

    assert job.ok == 1
    assert job.done == 1


def test_manager_cancels_queued_job():
    FakeDownloader.finish_immediately = False
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=1)

    first = manager.submit("first", "download", [_song(0)], {})
    second = manager.submit("second", "download", [_song(1)], {})

    assert _wait_until(lambda: len(FakeDownloader.instances) == 1)
    assert manager.cancel(second) is True
    snapshot = {item["id"]: item for item in manager.snapshot()}
    assert snapshot[second]["status"] == CANCELLED
    assert snapshot[first]["status"] == RUNNING

    FakeDownloader.gate.set()
    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)
    assert len(FakeDownloader.instances) == 1


def test_manager_aggregate_and_clear():
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=2)
    manager.submit("first", "download", [_song(0), _song(1)], {})
    manager.submit("second", "download", [_song(2)], {})

    assert _wait_until(
        lambda: all(item["status"] == DONE for item in manager.snapshot())
    )
    assert manager.active_count() == 0
    assert manager.aggregate() == (0, 0)

    manager.clear_finished()
    assert manager.snapshot() == []


def test_manager_records_history_once():
    recorded = []
    manager = DownloadManager(
        lambda options: FakeDownloader(options),
        history_recorder=recorded.append,
    )
    manager.submit("first", "download", [_song(0)], {})

    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)
    assert len(recorded) == 1
    assert recorded[0].name == "first"


def test_manager_unknown_job():
    manager = DownloadManager(lambda options: None)
    assert manager.song_progress("missing") == {}
    assert manager.job_options("missing") is None
    assert manager.cancel("missing") is False


class LoopDownloader:
    started = threading.Event()

    def __init__(self, settings=None):
        self.loop = asyncio.new_event_loop()
        self.progress_handler = FakeProgressHandler()

    def download_multiple_songs(self, songs):
        async def work():
            LoopDownloader.started.set()
            await asyncio.sleep(30)

        self.loop.run_until_complete(work())


def test_manager_cancels_running_job():
    LoopDownloader.started = threading.Event()
    manager = DownloadManager(lambda options: LoopDownloader(options), max_parallel=1)
    job_id = manager.submit("job", "download", [_song(0)], {})

    assert _wait_until(LoopDownloader.started.is_set)
    assert manager.cancel(job_id) is True
    assert _wait_until(lambda: manager.snapshot()[0]["status"] == CANCELLED, timeout=10)


def test_manager_retry_only_failed_songs():
    FakeDownloader.fail_urls = {_song(1).url}
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=2)
    job_id = manager.submit("first", "download", [_song(0), _song(1)], {})

    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)
    info = manager.snapshot()[0]
    assert info["errors"] == 1
    assert info["can_retry"] is True

    FakeDownloader.fail_urls = set()
    retry_id = manager.retry_failed(job_id)
    assert retry_id is not None

    data = manager.job_options(retry_id)
    assert data is not None
    _, _, songs, _ = data
    assert [song.url for song in songs] == [_song(1).url]

    assert _wait_until(lambda: manager.snapshot()[-1]["status"] == DONE)
    assert manager.snapshot()[-1]["errors"] == 0


def test_manager_retry_without_failures():
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=2)
    job_id = manager.submit("first", "download", [_song(0)], {})

    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)
    assert manager.retry_failed(job_id) is None


def test_manager_retry_requires_finished_job():
    FakeDownloader.finish_immediately = False
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=1)
    job_id = manager.submit("first", "download", [_song(0)], {})

    assert _wait_until(lambda: manager.snapshot()[0]["status"] == RUNNING)
    assert manager.retry_failed(job_id) is None

    FakeDownloader.gate.set()
    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)


def test_manager_retry_refreshes_m3u(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "spotdl.utils.m3u.gen_m3u_files",
        lambda songs, *args, **kwargs: calls.append([song.url for song in songs]),
    )
    monkeypatch.setattr(
        "spotdl.console.tui.library.present_songs",
        lambda songs, settings: list(songs),
    )

    FakeDownloader.fail_urls = {_song(1).url}
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=2)
    options = {"m3u": "out/{list[0]}.m3u8"}
    job_id = manager.submit("first", "download", [_song(0), _song(1)], options)

    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)

    FakeDownloader.fail_urls = set()
    retry_id = manager.retry_failed(job_id)
    assert retry_id is not None
    assert _wait_until(lambda: manager.snapshot()[-1]["status"] == DONE)

    assert _wait_until(lambda: bool(calls))
    assert set(calls[-1]) == {_song(0).url, _song(1).url}


class SilentFailDownloader:
    def __init__(self, settings=None):
        self.loop = asyncio.new_event_loop()
        self.progress_handler = FakeProgressHandler()

    def download_multiple_songs(self, songs):
        return [(song, None) for song in songs]


def test_manager_reconciles_silent_failures():
    manager = DownloadManager(lambda options: SilentFailDownloader(options))
    manager.submit("job", "download", [_song(0), _song(1)], {})

    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)
    info = manager.snapshot()[0]
    assert info["errors"] == 2
    assert info["can_retry"] is True


def _real_song(index):
    from spotdl.types.song import Song

    return Song.from_missing_data(
        name=f"Song {index}",
        artists=["Artist"],
        artist="Artist",
        url=f"https://example.com/track/{index}",
    )


def test_manager_retry_with_links_sets_download_url_only_for_linked_songs():
    songs = [_real_song(0), _real_song(1), _real_song(2)]
    FakeDownloader.fail_urls = {songs[1].url, songs[2].url}
    manager = DownloadManager(lambda options: FakeDownloader(options), max_parallel=1)
    job_id = manager.submit("first", "download", songs, {})
    assert _wait_until(lambda: manager.snapshot()[0]["status"] == DONE)

    assert [song.url for song in manager.failed_songs(job_id)] == [
        songs[1].url,
        songs[2].url,
    ]

    link = "https://music.youtube.com/watch?v=abc"
    retry_id = manager.retry_failed(job_id, {songs[1].url: link})
    assert retry_id is not None

    _, _, retried, _ = manager.job_options(retry_id)
    by_url = {song.url: song for song in retried}
    assert by_url[songs[1].url].download_url == link
    assert by_url[songs[2].url].download_url is None
    assert songs[1].download_url is None
