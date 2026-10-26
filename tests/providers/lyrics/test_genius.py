import pytest
from rapidfuzz import fuzz

from spotdl.providers.lyrics.genius import Genius

DOCS_RATE_LIMIT = {
    "meta": {
        "status": 429,
        "message": (
            "You have reached the docs API limit of 100 requests per an hour. "
            "The Genius API Docs client is only meant for testing the API."
        ),
    }
}

PUBLIC_SONG_SEARCH = {
    "meta": {"status": 200},
    "response": {
        "sections": [
            {
                "type": "song",
                "hits": [
                    {
                        "type": "song",
                        "result": {
                            "id": 3374613,
                            "full_title": "Linked by Jim Yosef",
                            "url": "https://genius.com/Jim-yosef-and-anna-yvette-linked-lyrics",
                        },
                    },
                    {
                        "type": "artist",
                        "result": {
                            "name": "Jim Yosef",
                            "url": "https://genius.com/artists/Jim-yosef",
                        },
                    },
                ],
            }
        ]
    },
}


def _response(mocker, *, ok, status_code, url, payload=None, text=""):
    response = mocker.Mock()
    response.ok = ok
    response.status_code = status_code
    response.url = url
    response.text = text
    response.json.return_value = payload if payload is not None else {}
    return response


lyrics = "[Verse 1]\nMore than lovers\nDestined to find one another\nLike lightning and thunder\nCan't have one without the other (woah)\n\n[Chorus]\nIt was written in the stars\nOh, we can't be torn apart\nWe are linked together\nForged in fire forever\nWe are linked together, together\n\n[Drop]\n\n[Verse 2]\nPast the rings of Saturn\nAcross the Milky Way\nWhere it's raining diamonds\nWe'll return someday\nSpeaking life of words\nIn perfect harmony\nI'll run away with you to another galaxy\n[Chorus]\nIt was written in the stars\nOh, we can't be torn apart\nWe are linked together\nForged in fire forever\nWe are linked together, together\n\n[Drop]\n\n[Outro]\nWe are linked, together\nWe are linked, together\nWe are linked, together\nWe are linked, together\n(Oh, woah)"


@pytest.mark.vcr()
def test_get_genius_lyrics():
    genius = Genius("alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG")

    result = genius.get_lyrics("Linked", ["Jim Yosef"])

    assert result is not None

    assert fuzz.ratio(result, lyrics) > 80


def test_get_results_uses_public_search_when_docs_api_is_rate_limited(mocker):
    genius = Genius("test-token")
    docs = _response(
        mocker,
        ok=False,
        status_code=429,
        url="https://api.genius.com/search?q=Linked+-+Jim+Yosef",
        payload=DOCS_RATE_LIMIT,
    )
    public = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://genius.com/api/search/song?q=Linked+-+Jim+Yosef",
        payload=PUBLIC_SONG_SEARCH,
    )
    genius.session.get = mocker.Mock(side_effect=[docs, public])

    results = genius.get_results("Linked", ["Jim Yosef"])

    assert results == {
        "Linked by Jim Yosef": "https://genius.com/Jim-yosef-and-anna-yvette-linked-lyrics"
    }
    assert [call.args[0] for call in genius.session.get.call_args_list] == [
        "https://api.genius.com/search",
        "https://genius.com/api/search/song",
    ]
    public_headers = genius.session.get.call_args_list[1].kwargs["headers"]
    assert "authorization" not in {key.lower() for key in public_headers}


def test_rate_limited_docs_api_is_not_retried(mocker):
    genius = Genius("test-token")
    docs = _response(
        mocker,
        ok=False,
        status_code=429,
        url="https://api.genius.com/search?q=Linked+-+Jim+Yosef",
        payload=DOCS_RATE_LIMIT,
    )
    first = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://genius.com/api/search/song?q=Linked+-+Jim+Yosef",
        payload=PUBLIC_SONG_SEARCH,
    )
    second = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://genius.com/api/search/song?q=Linked+-+Jim+Yosef",
        payload=PUBLIC_SONG_SEARCH,
    )
    genius.session.get = mocker.Mock(side_effect=[docs, first, second])

    genius.get_results("Linked", ["Jim Yosef"])
    genius.get_results("Linked", ["Jim Yosef"])

    assert [call.args[0] for call in genius.session.get.call_args_list] == [
        "https://api.genius.com/search",
        "https://genius.com/api/search/song",
        "https://genius.com/api/search/song",
    ]


def test_get_results_keeps_song_ids_from_the_docs_api(mocker):
    genius = Genius("test-token")
    docs = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://api.genius.com/search?q=Linked+-+Jim+Yosef",
        payload={
            "meta": {"status": 200},
            "response": {
                "hits": [
                    {
                        "type": "song",
                        "result": {
                            "id": 3374613,
                            "full_title": "Linked by Jim Yosef",
                            "url": "https://genius.com/Jim-yosef-and-anna-yvette-linked-lyrics",
                        },
                    }
                ]
            },
        },
    )
    genius.session.get = mocker.Mock(return_value=docs)

    assert genius.get_results("Linked", ["Jim Yosef"]) == {
        "Linked by Jim Yosef": 3374613
    }
    genius.session.get.assert_called_once()


def test_get_results_reads_song_sections_from_the_docs_api(mocker):
    genius = Genius("test-token")
    docs = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://api.genius.com/search?q=Linked+-+Jim+Yosef",
        payload=PUBLIC_SONG_SEARCH,
    )
    genius.session.get = mocker.Mock(return_value=docs)

    assert genius.get_results("Linked", ["Jim Yosef"]) == {
        "Linked by Jim Yosef": 3374613
    }
    genius.session.get.assert_called_once()


def test_get_results_falls_back_when_docs_payload_has_no_response(mocker):
    genius = Genius("test-token")
    docs = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://api.genius.com/search?q=Linked+-+Jim+Yosef",
        payload={"meta": {"status": 200, "message": "Unknown API error"}},
    )
    public = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://genius.com/api/search/song?q=Linked+-+Jim+Yosef",
        payload=PUBLIC_SONG_SEARCH,
    )
    genius.session.get = mocker.Mock(side_effect=[docs, public])

    results = genius.get_results("Linked", ["Jim Yosef"])

    assert results["Linked by Jim Yosef"].startswith("https://genius.com/")


def test_extract_lyrics_from_song_page_url(mocker):
    genius = Genius("test-token")
    page = _response(
        mocker,
        ok=True,
        status_code=200,
        url="https://genius.com/Jim-yosef-and-anna-yvette-linked-lyrics",
        text="<html><div class='lyrics'>We are linked together</div></html>",
    )
    genius.session.get = mocker.Mock(return_value=page)

    lyrics = genius.extract_lyrics(
        "https://genius.com/Jim-yosef-and-anna-yvette-linked-lyrics"
    )

    assert lyrics == "We are linked together"
    assert genius.session.get.call_args.args[0] == (
        "https://genius.com/Jim-yosef-and-anna-yvette-linked-lyrics"
    )
