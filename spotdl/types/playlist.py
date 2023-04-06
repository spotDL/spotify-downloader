"""
Playlist module for retrieving playlist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from spotdl.types.song import Song, SongList
from spotdl.utils.spotify import SpotifyClient

__all__ = ["Playlist", "PlaylistError"]


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

        playlist = spotify_client.playlist(url)
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
                    key=lambda i: 0
                    if i["width"] is None or i["height"] is None
                    else i["width"] * i["height"],
                )["url"]
                if (len(playlist["images"]) > 0)
                else ""
            ),
        }

        playlist_response = spotify_client.playlist_items(url)
        if playlist_response is None:
            raise PlaylistError(f"Wrong playlist id: {url}")

        # Get all tracks from playlist
        tracks = playlist_response["items"]
        while playlist_response["next"]:
            playlist_response = spotify_client.next(playlist_response)

            # Failed to get response, break the loop
            if playlist_response is None:
                break

            # Add tracks to the list
            tracks.extend(playlist_response["items"])

        songs = []
        for track in tracks:
            if (
                not isinstance(track, dict)
                or track.get("track") is None
                or track.get("track", {}).get("is_local")
            ):
                continue

            track_meta = track.get("track", {})
            track_id = track_meta.get("id")
            if (
                track_meta == {}
                or track_id is None
                or track_meta.get("duration_ms") == 0
            ):
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
                album_artist=album_meta.get("artists", [])[0]["name"]
                if album_meta.get("artists")
                else None,
                disc_number=track_meta["disc_number"],
                duration=track_meta["duration_ms"],
                year=release_date[:4] if release_date else None,
                date=release_date,
                track_number=track_meta["track_number"],
                tracks_count=album_meta.get("total_tracks"),
                song_id=track_meta["id"],
                explicit=track_meta["explicit"],
                url=track_meta["external_urls"]["spotify"],
                isrc=track_meta.get("external_ids", {}).get("isrc"),
                cover_url=max(
                    album_meta["images"], key=lambda i: i["width"] * i["height"]
                )["url"]
                if (len(album_meta.get("images", [])) > 0)
                else None,
            )

            songs.append(song)

        return metadata, songs
