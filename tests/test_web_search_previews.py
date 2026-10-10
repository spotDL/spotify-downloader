"""Search cards must not wait for full download metadata."""

import pytest

from spotdl.types.song import Song
from spotdl.utils.web_search import get_search_results


def test_search_uses_preview_metadata_only(monkeypatch):
    monkeypatch.setattr(
        Song,
        "search",
        lambda term: {
            "tracks": {
                "items": [
                    {
                        "id": "track-id",
                        "name": "Y cómo es él",
                        "artists": [{"name": "José Luis Perales"}],
                        "album": {
                            "name": "Entre el agua y el fuego",
                            "images": [{"url": "cover"}],
                        },
                        "explicit": False,
                    }
                ]
            }
        },
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Preview fetched full track metadata")

    monkeypatch.setattr(Song, "from_url", forbidden)
    songs = get_search_results("perales")
    assert songs == [
        {
            "name": "Y cómo es él",
            "artists": ["José Luis Perales"],
            "album_name": "Entre el agua y el fuego",
            "cover_url": "cover",
            "explicit": False,
            "url": "https://open.spotify.com/track/track-id",
        }
    ]


def test_search_handles_missing_optional_metadata(monkeypatch):
    monkeypatch.setattr(
        Song,
        "search",
        lambda term: {
            "tracks": {"items": [{"id": "id", "name": "Song"}, {"name": "Unavailable"}]}
        },
    )
    songs = get_search_results("song")
    assert len(songs) == 1
    assert songs[0]["cover_url"] == ""
    assert songs[0]["artists"] == []


def test_search_keeps_provider_failure_visible(monkeypatch):
    def failed(term):
        raise RuntimeError("Spotify unavailable")

    monkeypatch.setattr(Song, "search", failed)
    with pytest.raises(RuntimeError, match="Spotify unavailable"):
        get_search_results("perales")
