from unittest.mock import Mock

import pytest
import requests

from spotdl.providers.lyrics.azlyrics import AzLyrics


def resp(text="", url="https://www.azlyrics.com/", history=(), ok=True):
    r = Mock(spec=requests.Response)
    r.text = text
    r.url = url
    r.history = history
    r.ok = ok
    return r


@pytest.fixture
def azlyrics():
    return AzLyrics()


def test_blocked_healthy_page(azlyrics):
    assert (
        azlyrics._blocked(
            resp("<title>Artist - Song lyrics</title><body><div>lyrics</div></body>")
        )
        is False
    )


def test_blocked_request_for_access_title(azlyrics):
    assert (
        azlyrics._blocked(
            resp(
                "<title>AZLyrics - request for access</title>",
                "https://www.azlyrics.com/search/",
            )
        )
        is True
    )


def test_blocked_unusual_activity_title(azlyrics):
    assert (
        azlyrics._blocked(
            resp(
                "<title>Our systems have detected unusual activity</title>",
                "https://www.azlyrics.com/lyrics/artist/song.html",
            )
        )
        is True
    )


def test_blocked_final_url_on_b_subnet(azlyrics):
    assert azlyrics._blocked(resp("", "https://b.azlyrics.com/?u=/search/")) is True


def test_blocked_redirect_hop_on_b_subnet(azlyrics):
    r = resp(
        "",
        "https://www.azlyrics.com/",
        history=(
            resp("", "https://www.azlyrics.com/"),
            resp("", "https://b.azlyrics.com/?u=/"),
        ),
    )
    assert azlyrics._blocked(r) is True


def test_wall_served_on_homepage(azlyrics):
    azlyrics.session.get = Mock(
        side_effect=[
            resp(
                "<title>AZLyrics - request for access</title>",
                "https://b.azlyrics.com/",
            ),
        ]
    )
    assert azlyrics._get_x_code() is None
    assert azlyrics._is_blocked


def test_wall_served_on_geo_js(azlyrics):
    azlyrics.session.get = Mock(
        side_effect=[
            resp("<title>AZLyrics</title>"),
            resp(
                "<title>AZLyrics - request for access</title>",
                "https://b.azlyrics.com/",
            ),
        ]
    )
    assert azlyrics._get_x_code() is None
    assert azlyrics._is_blocked


def test_wall_served_on_search(azlyrics):
    azlyrics._is_blocked = True
    azlyrics.session.get = Mock()  # must not be called once blocked
    assert azlyrics.get_results("Song", ["Artist"]) == {}
    azlyrics.session.get.assert_not_called()


def test_wall_served_on_lyrics_page(azlyrics):
    azlyrics.session.get = Mock(
        return_value=resp(
            "<title>AZLyrics - request for access</title>", "https://b.azlyrics.com/"
        )
    )
    assert azlyrics.extract_lyrics("https://www.azlyrics.com/lyrics/a/s.html") is None
    assert azlyrics._is_blocked
