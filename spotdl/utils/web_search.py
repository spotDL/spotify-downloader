"""Lightweight Spotify search previews for the web interface."""

from typing import Any, Dict, List

from spotdl.types.song import Song


def get_search_results(search_term: str) -> List[Dict[str, Any]]:
    """Show search metadata without fetching each track, artist and album.

    Download requests still resolve the selected track through parse_query.
    """
    response = Song.search(search_term)
    previews = []
    for track in response.get("tracks", {}).get("items", []):
        track_id = track.get("id")
        if not track_id or not track.get("name"):
            continue
        album = track.get("album") or {}
        images = album.get("images") or []
        previews.append(
            {
                "name": track["name"],
                "artists": [artist["name"] for artist in track.get("artists", [])],
                "album_name": album.get("name", ""),
                "cover_url": images[0].get("url", "") if images else "",
                "explicit": track.get("explicit", False),
                "url": "https://open.spotify.com/track/" + track_id,
            }
        )
    return previews
