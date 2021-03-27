"""
Provides all defaults-layer functionality for `SongObj` generation except the `SongObj` class
itself
"""

# ===============
# === Imports ===
# ===============
import typing

from textwrap import shorten
from ytmusicapi import YTMusic
from bs4 import BeautifulSoup
from requests import get


# =============================
# === main / defaults-layer ===
# =============================


def get_youtube_link(
    song_name: str, song_artists: typing.List["str"], album: str, song_duration: int
) -> typing.Optional[str]:
    """
    attempts to find "THE" youtube link to the song according to inputs
    """

    # !get search results from YTMusic
    search_results = __query_ytmusic(song_name=song_name, song_artists=song_artists)

    if len(search_results) == 0:
        return None

    # !keep track of top result
    # when a result has a higher "match score" than the top_match_score, the top_match_score
    # and top_match_link are both updated, once all the results are checked, you end up with
    # the top-most result which is theoretically the best/correct match
    top_match_score = 0
    top_match_link = None

    for result in search_results:
        # !calc avg match

        # each result contains the following, it would do well to note this somewhere, we'll
        # be refering to these dict-keys a lot in the next few lines
        #   - songName
        #   - songArtists (list, lower case)
        #   - albumName
        #   - duration (number of seconds, int)
        #   - link

        # song name match
        # name_match = common words in the name / total words in the supplied name
        name_match = __common_elm_fraction(
            source=song_name.split(" "), result=result["songName"].split(" ")
        )

        if name_match < 0.25:
            # skip result, it's probably not a good match, less than 1 out of 4 words
            # from the supplied name are in the result
            continue

        # song artist match
        # same as name_match but here its about the contributing artists instead
        artist_match = __common_elm_fraction(
            source=song_artists, result=result["songArtists"]
        )

        # song duration match
        # duration_match = 1 - (time delta in sec/15 sec), the idea is that 1 indicates the best
        # possible score and 0 indicates the lease score, if a score is less than zero, the result
        # will be dropped, if the time difference is greater than 15 sec, is not the correct match
        # anyways
        duration_match = 1 - (abs(result["duration"] - song_duration) / 15)

        if duration_match < 0:
            # skip this result
            continue

        # album_match
        # if results is a song: album_match = 1 if its a perfect match, else skip the result
        # because, even if the other match scores are good, it's definitely a different song
        #
        # if result is an album: album_match = 0
        #
        # note that the albumName in the result will be lower case
        if result["albumName"] == album.lower():
            album_match = 1
        elif result["albumName"] != "":
            continue
        else:
            album_match = 0

        # avg match
        avg_match = (name_match + artist_match + album_match + duration_match) / 4

        # !update top match as required
        if avg_match > top_match_score:
            top_match_score = avg_match
            # top_match_link is always a str but mypy doesn't recognize it as such, so we wrap it
            # in a str() conversion so mypy will shut up on the final return statement
            top_match_link = str(result["link"])

    if top_match_score < 0.75:
        result_song_name = result["songName"]

        file = open("possible errors (delete when ever you want).txt", "ab")
        file.write(
            f"{shorten(song_artists[0], 15):>15s} - {shorten(song_name, 40):40s} "
            f"{top_match_score:0.2f}pt {top_match_link}: {result_song_name}\n".encode(),
        )
        file.close()

    return top_match_link


# ================================================
# === support / background / private functions ===
# ================================================
def __query_ytmusic(
    song_name: str, song_artists: typing.List[str]
) -> typing.List[dict]:
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
        artist_str += artist.join(", ")

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
        # !skip bad results (missing keys/NoneType results)
        skip_result = False

        for key in ["artists", "album", "resultType", "duration", "title"]:
            # NOTE: if key is not in the dict, NoneType is returned
            if result.get(key) is None:
                # video results do not have album metadata
                if not (result["resultType"] == "video" and key == "album"):
                    # placing the continue statement here will skip to the next
                    # key and not the next result, hence the convoluted scheme
                    skip_result = True

        if skip_result:
            continue

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
        # Sometimes, duration itself is not returned, we can't evaluate such results,
        # they are dropped
        except ValueError:
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


def __prepare_list(list_str: typing.List[str]):
    for word in list_str:
        list_str.remove(word)

        if not word.isalnum():
            n_word = word.lower()

            for letter in n_word:
                if not letter.isalnum():
                    n_word = n_word.replace(letter, "")

            if n_word != "":
                list_str.append(n_word)

        else:
            list_str.append(word.lower())

    return list_str


def __is_similar(word_a: str, word_b: str):
    if word_a == word_b:
        return True

    # yes, you would expect an elif statement here, but that is apparently against pylint's
    # sensibilities. See: https://stackoverflow.com/q/63755912
    if len(word_a) != len(word_b):
        return False

    hit_count = 0

    for _index in range(len(word_a)):
        if word_a[_index] != word_b[_index]:
            hit_count += 1

    if hit_count < 2:
        return True

    return False


def __common_elm_fraction(source: typing.List[str], result: typing.List[str]) -> float:

    src = __prepare_list(source)
    res = __prepare_list(result)

    similar_word_count = 0

    for src_word in src:
        for res_word in res:
            if __is_similar(src_word, res_word):
                similar_word_count += 1
                break

    return similar_word_count / len(src)


def get_song_lyrics(song_name: str, song_artists: typing.List[str]) -> str:
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
