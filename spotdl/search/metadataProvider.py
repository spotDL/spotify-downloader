from requests import get
from bs4 import BeautifulSoup
from spotdl.search.spotifyClient import SpotifyClient
from typing import List


def from_url(spotifyURL: str):
    if not ("open.spotify.com" in spotifyURL and "track" in spotifyURL):
        raise Exception("passed URL is not that of a track: %s" % spotifyURL)

    # query spotify for song, artist, album details
    spotifyClient = SpotifyClient()

    rawTrackMeta = spotifyClient.track(spotifyURL)

    primaryArtistId = rawTrackMeta["artists"][0]["id"]
    rawArtistMeta = spotifyClient.artist(primaryArtistId)

    albumId = rawTrackMeta["album"]["id"]
    rawAlbumMeta = spotifyClient.album(albumId)

    return rawTrackMeta, rawArtistMeta, rawAlbumMeta


def get_song_lyrics(song_name: str, song_artists: List[str]) -> str:
    """
    `str` `song_name` : name of song

    `list<str>` `song_artists` : list containing name of contributing artists

    RETURNS `str`: Lyrics of the song.

    Gets the metadata of the song.
    """

    headers = {
        "Authorization": "Bearer alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG",
    }
    api_search_url = "https://api.genius.com/search"
    search_query = f'{song_name} {", ".join(song_artists)}'

    api_response = get(
        api_search_url, params={"q": search_query}, headers=headers
    ).json()

    song_id = api_response["response"]["hits"][0]["result"]["id"]
    song_api_url = f"https://api.genius.com/songs/{song_id}"

    api_response = get(song_api_url, headers=headers).json()

    song_url = api_response["response"]["song"]["url"]

    genius_page = get(song_url)
    soup = BeautifulSoup(genius_page.text, "html.parser")
    lyrics = soup.select_one("div.lyrics").get_text()

    return lyrics.strip()
