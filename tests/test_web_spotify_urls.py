"""Regression tests for localized Spotify URLs."""

import pytest

from spotdl.utils.web import normalize_spotify_url, validate_search_term


@pytest.mark.parametrize("resource", ["track", "album", "playlist", "artist"])
@pytest.mark.parametrize("locale", ["es", "en", "pt-BR"])
def test_normalize_localized_spotify_url(resource, locale):
    original = (
        f"https://open.spotify.com/intl-{locale}/{resource}/example"
        "?si=share-token#fragment"
    )
    expected = f"https://open.spotify.com/{resource}/example" "?si=share-token#fragment"
    result = normalize_spotify_url(original)
    assert result == expected
    assert validate_search_term(result)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Eminem - Without Me",
        "https://example.com/intl-es/track/example",
        "https://open.spotify.com.example.com/intl-es/track/example",
        "https://user@open.spotify.com/intl-es/track/example",
        "spotify:track:example",
        "https://[invalid",
        "https://open.spotify.com/track/example?si=token",
    ],
)
def test_leave_other_inputs_unchanged(value):
    assert normalize_spotify_url(value) == value


def test_trim_spotify_url_whitespace():
    assert (
        normalize_spotify_url("  https://open.spotify.com/intl-es/track/example  ")
        == "https://open.spotify.com/track/example"
    )


def test_normalization_is_idempotent():
    value = "https://open.spotify.com/intl-es/playlist/example"
    normalized = normalize_spotify_url(value)
    assert normalize_spotify_url(normalized) == normalized
