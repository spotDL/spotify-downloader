from spotdl.console.tui import history as history_module
from spotdl.console.tui.library import missing_songs, present_songs, song_file_exists
from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name


def _song():
    return Song.from_missing_data(
        name="Song",
        artists=["Artist"],
        artist="Artist",
        album_name="Album",
        duration=180,
        url="https://open.spotify.com/track/library_song",
    )


def _settings(tmp_path):
    return {
        "output": str(tmp_path / "{artists} - {title}.{output-ext}"),
        "format": "mp3",
        "restrict": None,
        "max_filename_length": None,
        "detect_formats": None,
    }


def test_song_file_exists(tmp_path):
    song = _song()
    settings = _settings(tmp_path)

    assert song_file_exists(song, settings) is False
    assert missing_songs([song], settings) == [song]
    assert present_songs([song], settings) == []

    expected = create_file_name(song, settings["output"], "mp3", None, False, None)
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.write_text("x", encoding="utf-8")

    assert song_file_exists(song, settings) is True
    assert missing_songs([song], settings) == []
    assert present_songs([song], settings) == [song]


def test_song_file_exists_without_output(tmp_path):
    assert song_file_exists(_song(), {}) is False


def test_history_stores_failed_and_options(tmp_path, monkeypatch):
    monkeypatch.setattr(history_module, "HISTORY_FILE", tmp_path / "tui_history.json")
    history_module.clear_history()
    history_module.add_download_entry(
        name="Playlist",
        url="https://open.spotify.com/playlist/abc",
        count=3,
        ok=1,
        err=2,
        failed=[{"url": "https://open.spotify.com/track/a", "name": "A"}],
        options={"m3u": "out/{list[0]}.m3u8", "format": "mp3"},
    )

    entry = history_module.load_history()["downloads"][0]
    assert entry["failed"] == [{"url": "https://open.spotify.com/track/a", "name": "A"}]
    assert entry["options"] == {"m3u": "out/{list[0]}.m3u8", "format": "mp3"}
