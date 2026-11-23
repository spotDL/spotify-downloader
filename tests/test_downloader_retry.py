from spotdl.download import downloader as downloader_module
from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.config import DOWNLOADER_OPTIONS


def make_downloader(tmp_path):
    settings = dict(DOWNLOADER_OPTIONS)
    settings["output"] = str(tmp_path / "{artists} - {title}.{output-ext}")
    settings["simple_tui"] = True
    settings["lyrics_providers"] = []
    return Downloader(settings)


def make_song():
    return Song.from_missing_data(
        name="Accidente",
        artists=["Las Ligas Menores"],
        artist="Las Ligas Menores",
        album_name="Las Ligas Menores",
        url="https://open.spotify.com/track/abc123",
        song_id="abc123",
    )


def test_existing_file_is_skipped_before_reinit(tmp_path, monkeypatch):
    downloader = make_downloader(tmp_path)
    existing = tmp_path / "Las Ligas Menores - Accidente.mp3"
    existing.write_bytes(b"")

    def fail_reinit(song):
        raise AssertionError("reinit_song must not run for an existing file")

    monkeypatch.setattr(downloader_module, "reinit_song", fail_reinit)

    song, path = downloader.loop.run_until_complete(
        downloader.async_search_and_download(make_song())
    )

    assert path == existing
    assert downloader.errors == []


def test_missing_file_still_reinits(tmp_path, monkeypatch):
    downloader = make_downloader(tmp_path)
    calls = []

    def record_reinit(song):
        calls.append(song.url)
        raise RuntimeError("Could not get session")

    monkeypatch.setattr(downloader_module, "reinit_song", record_reinit)

    _, path = downloader.loop.run_until_complete(
        downloader.async_search_and_download(make_song())
    )

    assert path is None
    assert calls == ["https://open.spotify.com/track/abc123"]


def test_force_overwrite_does_not_skip_existing_file(tmp_path, monkeypatch):
    downloader = make_downloader(tmp_path)
    downloader.settings["overwrite"] = "force"
    (tmp_path / "Las Ligas Menores - Accidente.mp3").write_bytes(b"")
    calls = []

    def record_reinit(song):
        calls.append(song.url)
        raise RuntimeError("stop")

    monkeypatch.setattr(downloader_module, "reinit_song", record_reinit)

    downloader.loop.run_until_complete(
        downloader.async_search_and_download(make_song())
    )

    assert calls == ["https://open.spotify.com/track/abc123"]


def test_song_without_results_fails_with_lookup_error_and_is_not_retried(
    tmp_path, monkeypatch
):
    downloader = make_downloader(tmp_path)
    monkeypatch.setattr(downloader_module, "reinit_song", lambda song: song)
    monkeypatch.setattr(downloader, "search_primaries", lambda song: [])
    sleeps = []
    monkeypatch.setattr(downloader_module.time, "sleep", sleeps.append)

    results = downloader.download_multiple_songs([make_song()])

    assert results[0][1] is None
    assert any("LookupError" in error for error in downloader.errors)
    assert sleeps == []


def test_transient_failure_is_retried(tmp_path, monkeypatch):
    downloader = make_downloader(tmp_path)
    monkeypatch.setattr(downloader_module, "reinit_song", lambda song: song)
    monkeypatch.setattr(downloader, "search_primaries", lambda song: ["url"])
    monkeypatch.setattr(
        Downloader,
        "_download_first_candidate",
        staticmethod(lambda *args: (None, None, None)),
    )
    sleeps = []
    monkeypatch.setattr(downloader_module.time, "sleep", sleeps.append)

    downloader.download_multiple_songs([make_song()])

    assert sleeps == [downloader_module.RETRY_BASE_DELAY]
