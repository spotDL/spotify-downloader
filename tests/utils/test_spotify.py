import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
import spotapi

import spotdl.utils.spotify as spotify_module
from spotdl.utils.spotify import SpotifyClient, SpotifyError


def test_init(patch_dependencies):
    """
    Test SpotifyClient initialization
    """

    SpotifyClient.init(
        client_id="client_id",
        client_secret="client_secret",
        user_auth=False,
        no_cache=True,
    )

    assert SpotifyClient._instance is not None


def test_multiple_init():
    """
    Test multiple SpotifyClient initialization.
    It was initialized in the previous function so there is no need to initialize it again.
    """

    with pytest.raises(SpotifyError):
        SpotifyClient.init(
            client_id="client_id",
            client_secret="client_secret",
            user_auth=False,
            no_cache=True,
        )
        SpotifyClient.init(
            client_id="client_id",
            client_secret="client_secret",
            user_auth=False,
            no_cache=True,
        )


def test_init_uses_free_client_by_default(monkeypatch):
    """
    Test SpotifyClient uses SpotipyFree unless the official API is requested.
    """

    client = object()
    calls = []

    def fake_free_client(**kwargs):
        calls.append(("free", kwargs))
        return client

    def fake_official_client(**kwargs):
        calls.append(("official", kwargs))
        return object()

    monkeypatch.setattr(SpotifyClient, "_instance", None)
    monkeypatch.setattr(SpotifyClient, "_use_official_api", False)
    monkeypatch.setattr(spotify_module, "_init_free_spotify_client", fake_free_client)
    monkeypatch.setattr(
        spotify_module, "_init_official_spotify_client", fake_official_client
    )

    result = SpotifyClient.init(
        client_id="client_id",
        client_secret="client_secret",
    )

    assert result is client
    assert SpotifyClient() is client
    assert calls == [
        (
            "free",
            {
                "client_id": "client_id",
                "client_secret": "client_secret",
                "user_auth": False,
                "no_cache": False,
                "headless": False,
                "max_retries": 3,
                "use_cache_file": False,
                "auth_token": None,
                "cache_path": None,
            },
        )
    ]
    assert SpotifyClient._use_official_api is False


def test_init_uses_official_client_when_requested(monkeypatch):
    """
    Test SpotifyClient can opt into the official Spotipy client.
    """

    client = object()
    calls = []

    def fake_free_client(**kwargs):
        calls.append(("free", kwargs))
        return object()

    def fake_official_client(**kwargs):
        calls.append(("official", kwargs))
        return client

    monkeypatch.setattr(SpotifyClient, "_instance", None)
    monkeypatch.setattr(SpotifyClient, "_use_official_api", False)
    monkeypatch.setattr(spotify_module, "_init_free_spotify_client", fake_free_client)
    monkeypatch.setattr(
        spotify_module, "_init_official_spotify_client", fake_official_client
    )

    result = SpotifyClient.init(
        client_id="client_id",
        client_secret="client_secret",
        use_official_api=True,
    )

    assert result is client
    assert SpotifyClient() is client
    assert calls == [
        (
            "official",
            {
                "client_id": "client_id",
                "client_secret": "client_secret",
                "user_auth": False,
                "no_cache": False,
                "headless": False,
                "max_retries": 3,
                "use_cache_file": False,
                "auth_token": None,
                "cache_path": None,
            },
        )
    ]
    assert SpotifyClient._use_official_api is True


def test_init_uses_official_client_for_official_api_only_options(monkeypatch, caplog):
    """
    Test SpotifyClient routes official API only options to the official client.
    """

    client = object()
    calls = []

    def fake_free_client(**kwargs):
        calls.append(("free", kwargs))
        return object()

    def fake_official_client(**kwargs):
        calls.append(("official", kwargs))
        return client

    monkeypatch.setattr(SpotifyClient, "_instance", None)
    monkeypatch.setattr(SpotifyClient, "_use_official_api", False)
    monkeypatch.setattr(spotify_module, "_init_free_spotify_client", fake_free_client)
    monkeypatch.setattr(
        spotify_module, "_init_official_spotify_client", fake_official_client
    )
    caplog.set_level(logging.INFO, logger="spotdl.utils.spotify")

    result = SpotifyClient.init(
        client_id="client_id",
        client_secret="client_secret",
        user_auth=True,
        auth_token="auth_token",
        use_cache_file=True,
    )

    assert result is client
    assert calls[0][0] == "official"
    assert SpotifyClient._use_official_api is True
    assert "Using the official Spotify Web API because" in caplog.text


@pytest.fixture
def chunk_transport(mocker):
    load = spotify_module._load_query_definitions
    load.cache_clear()
    transport = mocker.patch.object(spotify_module, "TLSClient").return_value
    transport.__enter__.return_value = transport
    mocker.patch.object(
        spotify_module,
        "extract_mappings",
        return_value=({1: "a", 2: "b"}, {1: "x", 2: "y"}),
    )
    yield transport
    load.cache_clear()


def test_query_chunks_load_concurrently_and_reuse_player_build(chunk_transport):
    barrier = threading.Barrier(2)

    def get(url):
        if "cdn/build" in url:
            barrier.wait(timeout=5)
        return SimpleNamespace(fail=False, response=url)

    chunk_transport.get.side_effect = get
    load = spotify_module._load_query_definitions
    first = load("player-v1.js")
    assert "x.a.js" in first and "y.b.js" in first
    assert load("player-v1.js") == first
    assert chunk_transport.get.call_count == 3
    assert load("player-v2.js").startswith("player-v2.js")
    assert chunk_transport.get.call_count == 6


def test_failed_chunk_load_is_retried_instead_of_cached(chunk_transport):
    responses = iter(
        [
            SimpleNamespace(fail=True, error=SimpleNamespace(string="CDN unavailable")),
            SimpleNamespace(fail=False, response="y.b.js"),
        ]
    )
    chunk_transport.get.side_effect = lambda url: (
        next(responses)
        if url.endswith("y.b.js")
        else SimpleNamespace(fail=False, response=url.rsplit("/", 1)[-1])
    )

    load = spotify_module._load_query_definitions
    with pytest.raises(spotify_module.BaseClientError):
        load("player.js")

    assert load("player.js") == "player.jsx.a.jsy.b.js"
    assert chunk_transport.get.call_count == 6


@pytest.fixture
def free_client(mocker):
    session = spotify_module._anonymous_session
    session.cache_clear()
    mocker.patch.object(spotify_module, "_thread_local", threading.local())
    yield spotify_module._init_free_spotify_client()
    session.cache_clear()


def test_free_client_isolates_tls_per_thread_and_reuses_session(mocker, free_client):
    session = spotify_module._anonymous_session()
    session.js_pack = "player.js"

    def get_token():
        session.access_token, session.client_token = "access", "client"

    token = mocker.patch.object(session, "get_client_token", side_effect=get_token)
    load = mocker.patch.object(
        spotify_module,
        "_load_query_definitions",
        return_value='"getTrack","query","hash"',
    )
    barrier = threading.Barrier(2)

    def worker(language):
        base = spotapi.Song(language=language).base
        barrier.wait(timeout=5)
        assert base.part_hash("getTrack") == "hash"
        headers = base.client.authenticate({})["headers"]
        assert headers["Authorization"] == "Bearer access"
        assert headers["Client-Token"] == "client"
        assert headers["Accept-Language"] == language
        return base.client

    with ThreadPoolExecutor(2) as executor:
        first, second = executor.map(worker, ("en", "de"))

    assert first is not second
    token.assert_called_once_with()
    load.assert_called_once_with("player.js")

    refresh = mocker.patch.object(session, "_handle_auth_failure", return_value=True)
    response = SimpleNamespace(status_code=401)
    session.access_token = "refreshed"
    for client in (first, second):
        assert client.on_auth_failure(response)
    refresh.assert_not_called()


def test_thread_tls_resets_after_request_error(mocker, free_client):
    first = spotapi.Song().base.client
    mocker.patch.object(
        spotify_module.TLSClient,
        "build_request",
        side_effect=spotify_module.RequestError("Failed to complete request."),
    )
    close = mocker.spy(first, "close")

    with pytest.raises(spotify_module.RequestError):
        first.build_request("GET", "https://example.com")

    close.assert_called_once_with()
    assert spotapi.Song().base.client is not first
