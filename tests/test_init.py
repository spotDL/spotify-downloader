from types import SimpleNamespace

import pytest

import spotdl.utils.config
from spotdl import Spotdl
from spotdl.types.song import Song
from spotdl.utils.config import DEFAULT_CONFIG, DOWNLOADER_OPTIONS
from spotdl.utils.spotify import SpotifyClient
from tests.conftest import new_initialize


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(spotdl.utils.config, "get_spotdl_path", lambda *_: tmp_path)
    data = SimpleNamespace()
    data.directory = tmp_path
    yield data


def test_get_urls(monkeypatch):
    """
    Tests if spotdl can be initialized correctly.
    """

    monkeypatch.setattr(SpotifyClient, "init", new_initialize)

    settings = DOWNLOADER_OPTIONS.copy()
    settings["simple_tui"] = True
    settings["log_level"] = "DEBUG"
    settings["lyrics_providers"] = ["genius", "musixmatch"]

    # Test if spotdl can be initialized with spotify credentials.
    spotdl_client = Spotdl(
        client_id=DEFAULT_CONFIG["client_id"],
        client_secret=DEFAULT_CONFIG["client_secret"],
        user_auth=DEFAULT_CONFIG["user_auth"],
        cache_path=DEFAULT_CONFIG["cache_path"],
        no_cache=True,
        headless=DEFAULT_CONFIG["headless"],
        downloader_settings=settings,
    )

    urls = spotdl_client.get_download_urls(
        [Song.from_url("https://open.spotify.com/track/0kx3ml8bdAYrQtcIwvkhp8")]
    )

    assert len(urls) == 1


def test_download(setup, monkeypatch, tmpdir):
    """
    Tests if spotdl can be initialized correctly.
    """

    monkeypatch.chdir(tmpdir)

    monkeypatch.setattr(SpotifyClient, "init", new_initialize)

    settings = DOWNLOADER_OPTIONS.copy()
    settings["simple_tui"] = True
    settings["log_level"] = "DEBUG"
    settings["lyrics_providers"] = ["genius", "musixmatch"]

    # Test if spotdl can be initialized with spotify credentials.
    spotdl_client = Spotdl(
        client_id=DEFAULT_CONFIG["client_id"],
        client_secret=DEFAULT_CONFIG["client_secret"],
        user_auth=DEFAULT_CONFIG["user_auth"],
        cache_path=DEFAULT_CONFIG["cache_path"],
        no_cache=True,
        headless=DEFAULT_CONFIG["headless"],
        downloader_settings=settings,
    )

    song = {
        "name": "Nobody Else",
        "artists": ["Abstrakt"],
        "artist": "Abstrakt",
        "album_id": "6ZQZ5Z1NQZJQY5Y7YJZJYJ",
        "album_name": "Nobody Else",
        "album_artist": "Abstrakt",
        "genres": [],
        "disc_number": 1,
        "disc_count": 1,
        "duration": 162.406,
        "year": 2022,
        "date": "2022-03-17",
        "track_number": 1,
        "tracks_count": 1,
        "isrc": "GB2LD2210007",
        "song_id": "0kx3ml8bdAYrQtcIwvkhp8",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b27345f5ba253b9825efc88bc236",
        "explicit": False,
        "publisher": "NCS",
        "url": "https://open.spotify.com/track/0kx3ml8bdAYrQtcIwvkhp8",
        "copyright_text": "2022 NCS",
        "download_url": "https://www.youtube.com/watch?v=nfyk-V5CoIE",
    }

    assert None not in spotdl_client.download(Song.from_dict(song))
