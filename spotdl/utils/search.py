from typing import List

from spotdl.types.song import Song, SongError
from spotdl.utils.spotify import SpotifyClient


def get_search_results(search_term: str) -> List[Song]:
    """
    Creates a list of Song objects from a search term.
    """

    spotify_client = SpotifyClient()
    raw_search_results = spotify_client.search(search_term)

    if (
        raw_search_results is None
        or len(raw_search_results.get("tracks", {}).get("items", [])) == 0
    ):
        raise SongError("No songs matches found on spotify")

    songs = []
    for index, _ in enumerate(raw_search_results["tracks"]["items"]):
        songs.append(
            Song.from_url(
                "http://open.spotify.com/track/"
                + raw_search_results["tracks"]["items"][index]["id"]
            )
        )

    return songs
