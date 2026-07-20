from requests.exceptions import ConnectionError, JSONDecodeError

from spotdl.providers.audio import bandcamp
from spotdl.providers.audio.piped import API_BASE_URL, Piped
from spotdl.utils.config import GlobalConfig


class JsonResponse:
    def __init__(self, payload=None, status_code=200, invalid_json=False):
        self.payload = payload
        self.status_code = status_code
        self.invalid_json = invalid_json
        self.text = "<html>not json</html>" if invalid_json else ""

    def json(self):
        if self.invalid_json:
            raise JSONDecodeError("Expecting value", self.text, 0)

        return self.payload


class StaticSession:
    requested_url = None
    params = None
    proxies = None

    def __init__(self, responses):
        self.responses = iter(responses)

    def get(self, *args, **kwargs):
        self.requested_url = args[0]
        self.params = kwargs.get("params")
        self.proxies = kwargs.get("proxies")
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response

        return response


def bandcamp_track_payload(**overrides):
    payload = {
        "id": 2,
        "title": "Test Track",
        "tracks": [
            {
                "track_num": 1,
                "duration": 123,
                "is_streamable": True,
                "has_lyrics": True,
            }
        ],
        "is_set_price": False,
        "currency": "USD",
        "price": 0,
        "require_email": False,
        "is_purchasable": False,
        "free_download": False,
        "is_preorder": False,
        "tags": [],
        "art_id": 10,
        "band": {
            "band_id": 1,
            "name": "Test Artist",
        },
        "album_id": 3,
        "album_title": "Test Album",
        "label_id": 4,
        "label": "Test Label",
        "about": "",
        "credits": "",
        "release_date": 0,
        "bandcamp_url": "https://artist.bandcamp.com/track/test-track",
    }
    payload.update(overrides)
    return payload


def malformed_optional_bandcamp_payload():
    payload = bandcamp_track_payload(tags=None)
    for key in ("label_id", "label", "about", "credits", "release_date"):
        payload.pop(key)

    return payload


def install_bandcamp_get(monkeypatch, responses):
    responses_iter = iter(responses)

    def fake_get(*_args, **_kwargs):
        response = next(responses_iter)
        if isinstance(response, Exception):
            raise response

        return response

    monkeypatch.setattr(bandcamp.requests, "get", fake_get)


def piped_search_payload(items=None):
    return {
        "items": (
            items
            if items is not None
            else [
                {
                    "type": "channel",
                    "name": "Not a stream",
                },
                {
                    "name": "Missing type",
                },
                {
                    "type": "stream",
                    "url": "/watch?v=video_id",
                    "title": "Test Title",
                    "duration": 123,
                    "uploaderName": "Test Artist",
                    "views": 12345,
                },
            ]
        )
    }


def make_piped_provider(session):
    provider = Piped.__new__(Piped)
    provider.session = session
    return provider


def test_bandcamp_search_handles_invalid_json_and_malformed_rows(monkeypatch):
    monkeypatch.setattr(
        bandcamp.requests,
        "get",
        lambda *_args, **_kwargs: JsonResponse(invalid_json=True),
    )

    assert bandcamp.search("artist title") == []

    monkeypatch.setattr(
        bandcamp.requests,
        "get",
        lambda *_args, **_kwargs: JsonResponse(
            {
                "results": [
                    {"type": "t", "band_id": "1", "id": "2"},
                    {"type": "t", "id": "missing-band-id"},
                    None,
                    "not-a-row",
                    {"type": "t", "band_id": "3", "id": "4"},
                ]
            }
        ),
    )

    assert bandcamp.search("artist title") == [("1", "2"), ("3", "4")]


def test_bandcamp_get_results_handles_bad_candidates_and_optional_data(monkeypatch):
    skipped_cases = [
        ([("1", "2")], [JsonResponse(invalid_json=True)]),
        ([("1", "2")], [ConnectionError("failed")]),
        ([("1", "2")], [JsonResponse({"id": 2})]),
        ([("not-an-id", "2")], []),
        (
            [("1", "2")],
            [
                JsonResponse(bandcamp_track_payload(title=None)),
                JsonResponse(invalid_json=True),
            ],
        ),
    ]

    for found_tracks, responses in skipped_cases:
        monkeypatch.setattr(bandcamp, "search", lambda _term, ft=found_tracks: ft)
        install_bandcamp_get(monkeypatch, responses)

        assert bandcamp.BandCamp().get_results("artist title") == []

    kept_cases = [
        [
            JsonResponse(bandcamp_track_payload()),
            JsonResponse(invalid_json=True),
        ],
        [
            JsonResponse(malformed_optional_bandcamp_payload()),
            JsonResponse({"lyrics": []}),
        ],
    ]

    monkeypatch.setattr(bandcamp, "search", lambda _term: [("1", "2")])

    for responses in kept_cases:
        install_bandcamp_get(monkeypatch, responses)

        results = bandcamp.BandCamp().get_results("artist title")

        assert len(results) == 1
        assert results[0].url == "https://artist.bandcamp.com/track/test-track"


def test_piped_get_results_handles_failed_api_responses_and_malformed_rows():
    cases = [
        [JsonResponse(invalid_json=True)],
        [JsonResponse(status_code=502)],
        [ConnectionError("failed")],
        [JsonResponse({"error": "upstream failed"})],
    ]

    for responses in cases:
        session = StaticSession(responses)
        provider = make_piped_provider(session)

        assert provider.get_results("artist title") == []
        assert session.requested_url == f"{API_BASE_URL}/search"

    session = StaticSession(
        [
            JsonResponse(
                piped_search_payload(
                    [
                        {
                            "type": "stream",
                            "url": "/watch?missing=video_id",
                            "title": "Missing Video ID",
                            "duration": 123,
                            "uploaderName": "Test Artist",
                        },
                        {
                            "type": "stream",
                            "url": None,
                            "title": "Bad URL",
                            "duration": 123,
                            "uploaderName": "Test Artist",
                        },
                        {
                            "type": "stream",
                            "url": "/watch?v=bad_duration",
                            "title": "Bad Duration",
                            "duration": "123",
                            "uploaderName": "Test Artist",
                        },
                        {
                            "type": "stream",
                            "url": "/watch?v=video_id",
                            "title": "Test Title",
                            "duration": 123,
                            "uploaderName": "Test Artist",
                        },
                    ]
                )
            )
        ]
    )
    provider = make_piped_provider(session)

    results = provider.get_results("artist title")

    assert [result.result_id for result in results] == ["video_id"]


def test_piped_get_results_uses_api_proxy_isrc_and_canonical_youtube_url():
    session = StaticSession([JsonResponse(piped_search_payload())])
    provider = make_piped_provider(session)
    proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
    GlobalConfig.set_parameter("proxies", proxies)

    try:
        results = provider.get_results("USRC17607839")
    finally:
        GlobalConfig.set_parameter("proxies", None)

    assert session.requested_url == f"{API_BASE_URL}/search"
    assert session.params["filter"] == "music_songs"
    assert session.proxies == proxies
    assert results[0].url == "https://www.youtube.com/watch?v=video_id"
    assert results[0].views == 12345
    assert results[0].verified is True


def test_piped_get_download_metadata_delegates_to_yt_dlp_with_proxy(mocker):
    get = mocker.patch("spotdl.providers.audio.piped.requests.get")
    provider = Piped.__new__(Piped)
    provider.audio_handler = mocker.Mock()
    provider.audio_handler.params = {}
    provider.audio_handler.extract_info.return_value = {"id": "video_id"}
    proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
    GlobalConfig.set_parameter("proxies", proxies)

    try:
        metadata = provider.get_download_metadata(
            "https://www.youtube.com/watch?v=video_id"
        )
    finally:
        GlobalConfig.set_parameter("proxies", None)

    get.assert_not_called()
    assert metadata == {"id": "video_id"}
    assert provider.audio_handler.params["proxy"] == proxies["https"]
    provider.audio_handler.extract_info.assert_called_once_with(
        "https://www.youtube.com/watch?v=video_id",
        download=False,
    )
