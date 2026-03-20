"""
Playlist module for retrieving playlist data from Spotify.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from spotdl.types.song import Song, SongList
from spotdl.utils.spotify import SpotifyClient

__all__ = ["Playlist", "PlaylistError"]

logger = logging.getLogger(__name__)


class PlaylistError(Exception):
    """
    Base class for all exceptions related to playlists.
    """


@dataclass(frozen=True)
class Playlist(SongList):
    """
    Playlist class for retrieving playlist data from Spotify.
    """

    description: str
    author_url: str
    author_name: str
    cover_url: str

    @staticmethod
    def get_metadata(url: str) -> Tuple[Dict[str, Any], List[Song]]:
        """
        Get metadata for a playlist.

        ### Arguments
        - url: The URL of the playlist.

        ### Returns
        - A dictionary with metadata.
        """

        spotify_client = SpotifyClient()

        market = None
        try:
            profile = spotify_client.me()
            if profile:
                market = profile.get("country")
        except Exception:  # noqa: BLE001
            pass

        playlist = spotify_client.playlist(
            url, additional_types=("track",), market=market
        )
        if playlist is None:
            raise PlaylistError("Invalid playlist URL.")

        metadata = {
            "name": playlist["name"],
            "url": url,
            "description": playlist["description"],
            "author_url": playlist["external_urls"]["spotify"],
            "author_name": playlist["owner"]["display_name"],
            "cover_url": (
                max(
                    playlist["images"],
                    key=lambda i: (
                        0
                        if i["width"] is None or i["height"] is None
                        else i["width"] * i["height"]
                    ),
                )["url"]
                if (playlist.get("images") is not None and len(playlist["images"]) > 0)
                else ""
            ),
        }

        page = playlist.get("tracks")
        if page is None:
            page = playlist.get("items")
        if not isinstance(page, dict):
            raise PlaylistError(f"Wrong playlist id: {url}")

        def _row_track(row: Dict[str, Any]) -> Dict[str, Any]:
            t = row.get("track")
            if t is None:
                item = row.get("item")
                if isinstance(item, dict) and item.get("type") == "track":
                    t = item
            return {"track": t}

        raw_tracks = [_row_track(r) for r in page.get("items", [])]
        while page.get("next"):
            try:
                page = spotify_client.next(page)
            except Exception as exc:  # noqa: BLE001
                raise PlaylistError("Could not fetch next page of tracks.") from exc
            if page is None:
                break
            raw_tracks.extend(_row_track(r) for r in page.get("items", []))

        songs = []
        for track_no, track in enumerate(raw_tracks):
            if not isinstance(track, dict) or track.get("track") is None:
                continue

            track_meta = track["track"]

            if track_meta.get("is_local") or track_meta.get("type") != "track":
                logger.warning(
                    "Skipping track: %s local tracks and %s are not supported",
                    track_meta.get("id"),
                    track_meta.get("type"),
                )

                continue

            track_id = track_meta.get("id")
            if track_id is None or track_meta.get("duration_ms") == 0:
                continue

            album_meta = track_meta.get("album", {})
            release_date = album_meta.get("release_date")
            artists = [artist["name"] for artist in track_meta.get("artists", [])]
            song = Song.from_missing_data(
                name=track_meta["name"],
                artists=artists,
                artist=artists[0],
                album_id=album_meta.get("id"),
                album_name=album_meta.get("name"),
                album_artist=(
                    album_meta.get("artists", [])[0]["name"]
                    if album_meta.get("artists")
                    else None
                ),
                album_type=album_meta.get("album_type"),
                disc_number=track_meta["disc_number"],
                duration=int(track_meta["duration_ms"] / 1000),
                year=release_date[:4] if release_date else None,
                date=release_date,
                track_number=track_meta["track_number"],
                tracks_count=album_meta.get("total_tracks"),
                song_id=track_meta["id"],
                explicit=track_meta["explicit"],
                url=track_meta["external_urls"]["spotify"],
                isrc=track_meta.get("external_ids", {}).get("isrc"),
                cover_url=(
                    max(album_meta["images"], key=lambda i: i["width"] * i["height"])[
                        "url"
                    ]
                    if (len(album_meta.get("images", [])) > 0)
                    else None
                ),
                list_position=track_no + 1,
            )

            songs.append(song)

        return metadata, songs
