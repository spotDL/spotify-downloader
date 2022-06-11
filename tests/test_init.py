import pytest

from spotipy.oauth2 import SpotifyOauthError
from types import SimpleNamespace

from spotdl import Spotdl

from spotdl.types.song import Song
from spotdl.utils.config import DEFAULT_CONFIG
import spotdl.utils.config
from spotdl.utils.spotify import SpotifyClient
from tests.conftest import new_initialize


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(spotdl.utils.config, "get_spotdl_path", lambda *_: tmp_path)
    data = SimpleNamespace()
    data.directory = tmp_path
    yield data


def test_init_wrong_spotify_credentials():
    """
    Tests if exception is raised if no spotify credentials are given.
    """

    # Test if exception is raised if no spotify credentials are given.
    with pytest.raises(TypeError):
        Spotdl()  # type: ignore

    # Test if credentials are None
    with pytest.raises(SpotifyOauthError):
        Spotdl(None, None)  # type: ignore


@pytest.mark.vcr()
def test_get_urls():
    """
    Tests if spotdl can be initialized correctly.
    """

    # Test if spotdl can be initialized with spotify credentials.
    spotdl = Spotdl(
        client_id=DEFAULT_CONFIG["client_id"],
        client_secret=DEFAULT_CONFIG["client_secret"],
        user_auth=DEFAULT_CONFIG["user_auth"],
        cache_path=DEFAULT_CONFIG["cache_path"],
        no_cache=True,
        headless=DEFAULT_CONFIG["headless"],
        audio_providers=DEFAULT_CONFIG["audio_providers"],
        lyrics_providers=DEFAULT_CONFIG["lyrics_providers"],
        ffmpeg=DEFAULT_CONFIG["ffmpeg"],
        bitrate=DEFAULT_CONFIG["bitrate"],
        ffmpeg_args=DEFAULT_CONFIG["ffmpeg_args"],
        output_format=DEFAULT_CONFIG["format"],
        threads=DEFAULT_CONFIG["threads"],
        output=DEFAULT_CONFIG["output"],
        save_file=DEFAULT_CONFIG["save_file"],
        overwrite=DEFAULT_CONFIG["overwrite"],
        cookie_file=DEFAULT_CONFIG["cookie_file"],
        filter_results=DEFAULT_CONFIG["filter_results"],
        search_query=DEFAULT_CONFIG["search_query"],
        log_level="DEBUG",
        simple_tui=True,
        restrict=DEFAULT_CONFIG["restrict"],
        print_errors=DEFAULT_CONFIG["print_errors"],
    )

    urls = spotdl.get_download_urls(
        [Song.from_url("https://open.spotify.com/track/0kx3ml8bdAYrQtcIwvkhp8")]
    )

    assert len(urls) == 1


@pytest.mark.vcr()
def test_download(setup, monkeypatch):
    """
    Tests if spotdl can be initialized correctly.
    """

    monkeypatch.setattr(SpotifyClient, "init", new_initialize)

    # Test if spotdl can be initialized with spotify credentials.
    spotdl = Spotdl(
        client_id=DEFAULT_CONFIG["client_id"],
        client_secret=DEFAULT_CONFIG["client_secret"],
        user_auth=DEFAULT_CONFIG["user_auth"],
        cache_path=DEFAULT_CONFIG["cache_path"],
        no_cache=True,
        headless=DEFAULT_CONFIG["headless"],
        audio_providers=DEFAULT_CONFIG["audio_providers"],
        lyrics_providers=DEFAULT_CONFIG["lyrics_providers"],
        ffmpeg=DEFAULT_CONFIG["ffmpeg"],
        bitrate=DEFAULT_CONFIG["bitrate"],
        ffmpeg_args=DEFAULT_CONFIG["ffmpeg_args"],
        output_format=DEFAULT_CONFIG["format"],
        threads=DEFAULT_CONFIG["threads"],
        output=str(setup.directory.absolute()),
        save_file=DEFAULT_CONFIG["save_file"],
        overwrite=DEFAULT_CONFIG["overwrite"],
        cookie_file=DEFAULT_CONFIG["cookie_file"],
        filter_results=DEFAULT_CONFIG["filter_results"],
        search_query=DEFAULT_CONFIG["search_query"],
        log_level="DEBUG",
        simple_tui=True,
        restrict=DEFAULT_CONFIG["restrict"],
        print_errors=DEFAULT_CONFIG["print_errors"],
    )

    song = {
        "name": "Nobody Else",
        "artists": ["Abstrakt"],
        "artist": "Abstrakt",
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
        "song_list": None,
    }

    assert None not in spotdl.download(Song.from_dict(song))
