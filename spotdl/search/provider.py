"""
Provides all defaults-layer functionality for `SongObj` generation except the `SongObj` class
itself
"""

# ===============
# === Imports ===
# ===============
import typing as ty

from ytmusicapi import YTMusic
from bs4 import BeautifulSoup
from requests import get


# =============================
# === main / defaults-layer ===
# =============================


def get_youtube_link(
    song_name: str, song_artists: ty.List["str"], album: str, song_duration: int
) -> ty.Union[str, None]:
    """
    attempts to find "THE" youtube link to the song according to inputs
    """

    # !get search results from YTMusic
    search_results = __query_ytmusic(song_name=song_name, song_artists=song_artists)

    # !keep track of top result
    # when a result has a higher "match score" than the top_match_score, the top_match_score
    # and top_match_link are both updated, once all the results are checked, you end up with the
    # topmost result which is theoretically the best/correct match
    top_match_score = 0
    top_match_link = None

    for result in search_results:
        # !calc avg match

        # each result contains the following, it would do well to note this somewhere, we'll be
        # refering to these dict-keys a lot in the next few lines
        #   - songName
        #   - songArtists (list, lower case)
        #   - albumName
        #   - duration (number of seconds, int)
        #   - link

        # song name match
        # name_match = common words in the name / total words in the bigger name
        name_match = __common_elm_fraction(song_name, result["songName"])

        # song artist match
        # same as name_match but here its about the contributing artists instead
        #
        # `__common_elm_fraction` is case sensitive, the YTMusic results are strictly lowercase
        # so we need to enseure that the input metadata is also lowercase
        lower_case_artists = []

        for artist in song_artists:
            lower_case_artists.append(artist.lower())

        artist_match = __common_elm_fraction(lower_case_artists, result["songArtists"])

        # song duration match
        # duration_match = 1 - (time delta in sec/60 sec), the idea is that 1 indicates the best
        # possible score and 0 indicates the lease score, if a score is less than zero, the result
        # will be dropped, if the time difference is greater than 1 min, is not the correct match
        # anyways
        duration_match = 1 - (abs(result["duration"] - song_duration) / 60)

        if duration_match < 0:
            # skip this result
            continue

        # album_match
        # 1 if album name is the exact same, else the value is 0
        #
        # note that the albumName in the result will be lower case
        if result["albumName"] == album.lower():
            album_match = 1
        else:
            album_match = 0

        # avg match
        avg_match = (name_match + artist_match + album_match + duration_match) / 4

        # !update top match as required
        if avg_match > top_match_score:
            top_match_score = avg_match
            top_match_link = result["link"]

    # top_match_link is always a str but mypy doesn't recognize it as such, so we wrap it in a
    # str() conversion so mypy will shut up
    return str(top_match_link)


# ================================================
# === support / background / private functions ===
# ================================================
def __query_ytmusic(song_name: str, song_artists: ty.List[str]) -> list:
    """
    query YTMusic with "{artist names} - {song name}" and returns simplified song and video results
    as a `list[dict]`, each `dict` containing the following (in lower case):
        - songName
        - songArtists (list, lower case)
        - albumName
        - duration (number of seconds, int)
        - link

    NOTE: returns an empty string for album name if album name is not found.
    """

    # !construct a search string
    artist_str = ""
    for artist in song_artists:
        artist_str += artist + ", "

    # `[:-2]` removes trailing comma; eg. "Aiobahn, Rionos, " --> "Aiobahn, Rionos - Motivation"
    query = artist_str[:-2] + " - " + song_name

    # !create a YTMusic client
    ytm_client = YTMusic()

    # !search for both song and video results
    search_results = ytm_client.search(query=query, filter="videos")
    search_results += ytm_client.search(query=query, filter="songs")

    # all the simplified results will be stored in this
    collected_results = []

    # !simplify each result
    for result in search_results:
        # !contributing_artists
        r_artists = []
        for r_artist in result["artists"]:
            r_artists.append(r_artist["name"].lower())

        # !album_name
        r_album_name = ""
        if result["resultType"] == "song":
            r_album_name = result["album"]["name"].lower()

        # !duration
        try:
            # hh:mm:ss --> [ss, mm, hh]
            duration_bits = list(reversed(result["duration"].split(":")))
        
        # These errors get thrown when the duration returned is not in the form hh:mm:ss 
        except (TypeError, ValueError, AttributeError):
            continue

        if len(duration_bits) > 3:
            raise ValueError(f"supplied duration {result['duration']} is 1D+ in length")

        r_duration = 0
        for i in range(len(duration_bits)):
            # basically do seconds*1 + mins*60 +  hours * 3600
            r_duration += int(duration_bits[i]) * (60 ** i)
            
        collected_results.append(
            {
                "songName": result["title"],
                "songArtists": r_artists,
                "albumName": r_album_name,
                "duration": r_duration,
                "link": f"https://www.youtube.com/watch?v={result['videoId']}",
            }
        )

    return collected_results


def __common_elm_fraction(one: ty.Union[list, str], two: ty.Union[list, str]) -> float:
    """
    returns (number of common elements)/(total elements is bigger list/sentence).

    NOTE: in a sentence, each word is considered an element, i.e. "this is weird" ~ ["this", "is",
    "Weird"] has 3 elements
    """

    # !convert sentences to lists, this helps in the case one is a sentence and the other a list
    if isinstance(one, str):
        one = one.split(" ")

    if isinstance(two, str):
        two = two.split(" ")

    set1 = set(one)
    set2 = set(two)

    if len(set1) > len(set2):
        greater_length = len(set1)
    else:
        greater_length = len(set2)

    return len(set1.intersection(set2)) / greater_length


def get_song_lyrics(song_name: str, song_artists: ty.List[str]) -> str:
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
