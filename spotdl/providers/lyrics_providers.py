from requests import get
from bs4 import BeautifulSoup
from typing import List
from urllib.parse import quote

user_agent = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
(KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"
}


def get_lyrics_genius(song_name: str, song_artists: List[str]) -> str:
    """
    `str` `song_name` : name of song
    `list<str>` `song_artists` : list containing name of contributing artists
    RETURNS `str`: Lyrics of the song.
    Gets the lyrics of the song.
    """
    headers = {
        "Authorization": "Bearer alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG",
    }
    headers.update(user_agent)

    api_search_url = "https://api.genius.com/search"
    artist_str = ", ".join(
        artist for artist in song_artists if artist.lower() not in song_name.lower()
    )
    search_query = f"{song_name} {artist_str}"

    api_response = get(api_search_url, params={"q": search_query}, headers=headers)
    if not api_response.ok:
        return ""
    api_json = api_response.json()

    try:
        song_id = api_json["response"]["hits"][0]["result"]["id"]
    except (IndexError, KeyError):
        return ""

    song_api_url = f"https://api.genius.com/songs/{song_id}"
    api_response = get(song_api_url, headers=headers)
    if not api_response.ok:
        return ""
    api_json = api_response.json()

    song_url = api_json["response"]["song"]["url"]
    genius_page = get(song_url, headers=user_agent)
    if not genius_page.ok:
        return ""

    soup = BeautifulSoup(genius_page.text.replace("<br/>", "\n"), "html.parser")
    lyrics_div = soup.select_one("div.lyrics")

    if lyrics_div is not None:
        return lyrics_div.get_text().strip()

    lyrics_containers = soup.select("div[class^=Lyrics__Container]")
    lyrics = "\n".join(con.get_text() for con in lyrics_containers)
    return lyrics.strip()


def get_lyrics_musixmatch(
    song_name: str, song_artists: List[str], track_search=False
) -> str:
    """
    `str` `song_name` : Name of song
    `list<str>` `song_artists` : list containing name of contributing artists
    `bool` `track_search` : if `True`, search the musixmatch tracks page.
    RETURNS `str`: Lyrics of the song.
    Gets the lyrics of the song.
    """
    # remove artist names that are already in the song_name
    # we do not use SongObject.create_file_name beacause it
    # removes '/' etc from the artist and song names.
    artists_str = ", ".join(
        artist for artist in song_artists if artist.lower() not in song_name.lower()
    )

    # quote the query so that it's safe to use in a url
    # e.g "Au/Ra" -> "Au%2FRa"
    query = quote(f"{song_name} - {artists_str}", safe="")

    # search the `tracks page` if track_search is True
    if track_search:
        query += "/tracks"

    search_url = f"https://www.musixmatch.com/search/{query}"
    search_resp = get(search_url, headers=user_agent)
    if not search_resp.ok:
        return ""

    search_soup = BeautifulSoup(search_resp.text, "html.parser")
    song_url_tag = search_soup.select_one("a[href^='/lyrics/']")

    # song_url_tag being None means no results were found on the
    # All Results page, therefore, we use `track_search` to
    # search the tracks page.
    if song_url_tag is None:
        # track_serach being True means we are already searching the tracks page.
        if track_search:
            return ""

        lyrics = get_lyrics_musixmatch(song_name, song_artists, track_search=True)
        return lyrics

    song_url = "https://www.musixmatch.com" + str(song_url_tag.get("href", ""))
    lyrics_resp = get(song_url, headers=user_agent)
    if not lyrics_resp.ok:
        return ""

    lyrics_soup = BeautifulSoup(lyrics_resp.text, "html.parser")
    lyrics_paragraphs = lyrics_soup.select("p.mxm-lyrics__content")
    lyrics = "\n".join(i.get_text() for i in lyrics_paragraphs)

    return lyrics
