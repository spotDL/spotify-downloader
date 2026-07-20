import logging

import pytest

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
