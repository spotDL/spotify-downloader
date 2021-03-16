# ===============
# === Imports ===
# ===============

# ! the following are for the search provider to function
import typing
# ! Just for static typing
from typing import List

from rapidfuzz.fuzz import partial_ratio
from ytmusicapi import YTMusic
from bs4 import BeautifulSoup
from requests import get


# ================================
# === Note to readers / Coders ===
# ================================

# ! YTM search (the actual POST request), courtesy of Elliot G. (@rocketinventor)
# ! result parsing and song matching system by @Mikhail-Zex
# !
# ! Essentially, Without Elliot, you wouldn't have a YTM search provider at all.


# =======================
# === helper function ===
# =======================

def match_percentage(str1: str, str2: str, score_cutoff: float = 0) -> float:
    '''
    `str` `str1` : a random sentence

    `str` `str2` : another random sentence

    `float` `score_cutoff` : minimum score required to consider it a match
                             returns 0 when similarity < score_cutoff

    RETURNS `float`

    A wrapper around `rapidfuzz.fuzz.partial_ratio` to handle UTF-8 encoded
    emojis that usually cause errors
    '''

    # ! this will throw an error if either string contains a UTF-8 encoded emoji
    try:
        return partial_ratio(str1, str2, score_cutoff=score_cutoff)

    # ! we build new strings that contain only alphanumerical characters and spaces
    # ! and return the partial_ratio of that
    except:  # noqa:E722
        newStr1 = ''

        for eachLetter in str1:
            if eachLetter.isalnum() or eachLetter.isspace():
                newStr1 += eachLetter

        newStr2 = ''

        for eachLetter in str2:
            if eachLetter.isalnum() or eachLetter.isspace():
                newStr2 += eachLetter

        return partial_ratio(newStr1, newStr2, score_cutoff=score_cutoff)


# ========================================================================
# === Background functions/Variables (Not meant to be called directly) ===
# ========================================================================

# ! YTMusic api client
ytmApiClient = YTMusic()


def _parse_duration(duration: str) -> float:
    '''
    Convert string value of time (duration: "25:36:59") to a float value of seconds (92219.0)
    '''
    try:
        # {(1, "s"), (60, "m"), (3600, "h")}
        mappedIncrements = zip([1, 60, 3600], reversed(duration.split(":")))
        seconds = 0
        for multiplier, time in mappedIncrements:
            seconds += multiplier * int(time)
        return float(seconds)

    # ! This usually occurs when the wrong string is mistaken for the duration
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _map_result_to_song_data(result: dict) -> dict:
    song_data = {}
    if result['resultType'] in ['song', 'video']:
        artists = ", ".join(map(lambda a: a['name'], result['artists']))
        video_id = result['videoId']
        if video_id is None:
            return {}
        song_data = {
            'name': result['title'],
            'type': result['resultType'],
            'artist': artists,
            'length': _parse_duration(result.get('duration', None)),
            'link': f'https://www.youtube.com/watch?v={video_id}',
            'position': 0
        }
        if 'album' in result:
            song_data['album'] = result['album']['name']

    return song_data


def _query_and_simplify(searchTerm: str) -> List[dict]:
    '''
    `str` `searchTerm` : the search term you would type into YTM's search bar

    RETURNS `list<dict>`

    For structure of dict, see comment at function declaration
    '''

    # ! For dict structure, see end of this function (~ln 268, ln 283) and chill, this
    # ! function ain't soo big, there are plenty of comments and blank lines

    # build and POST a query to YTM

    print(f'Searching for: {searchTerm}')
    searchResult = ytmApiClient.search(searchTerm)

    return list(map(_map_result_to_song_data, searchResult))


# =======================
# === Search Provider ===
# =======================

def search_and_order_ytm_results(songName: str, songArtists: List[str],
                                 songAlbumName: str, songDuration: int) -> dict:
    '''
    `str` `songName` : name of song

    `list<str>` `songArtists` : list containing name of contributing artists

    `str` `songAlbumName` : name of song's album

    `int` `songDuration`

    RETURNS `dict`

    each entry in the result if formated as {'$YouTubeLink': $matchValue, ...}; Match value
    indicates how good a match the result is the the given parameters. THe maximum value
    that $matchValue can take is 100, the least value is unbound.
    '''
    # Query YTM
    results = _query_and_simplify(get_ytm_search_query(songName, songArtists))

    # Assign an overall avg match value to each result
    linksWithMatchValue = {}

    for result in results:
        # ! skip results without videoId, this happens if you are country restricted or
        # ! video is unavailabe
        if result == {}:
            continue

        # ! If there are no common words b/w the spotify and YouTube Music name, the song
        # ! is a wrong match (Like Ruelle - Madness being matched to Ruelle - Monster, it
        # ! happens without this conditional)

        # ! most song results on youtube go by $artist - $songName, so if the spotify name
        # ! has a '-', this function would return True, a common '-' is hardly a 'common
        # ! word', so we get rid of it. Lower-caseing all the inputs is to get rid of the
        # ! troubles that arise from pythons handling of differently cased words, i.e.
        # ! 'Rhino' == 'rhino' is false though the word is same... so we lower-case both
        # ! sentences and replace any hypens(-)
        lowerSongName = songName.lower()
        lowerResultName = result['name'].lower()

        sentenceAWords = lowerSongName.replace('-', ' ').split(' ')

        commonWord = False

        # ! check for common word
        for word in sentenceAWords:
            if word != '' and word in lowerResultName:
                commonWord = True

        # ! if there are no common words, skip result
        if not commonWord:
            continue

        # Find artist match
        # ! match  = (no of artist names in result) / (no. of artist names on spotify) * 100
        artistMatchNumber = 0

        # ! we use fuzzy matching because YouTube spellings might be mucked up
        if result['type'] == 'song':
            for artist in songArtists:
                if match_percentage(artist.lower(), result['artist'].lower(), 85):
                    artistMatchNumber += 1
        else:
            # ! i.e if video
            for artist in songArtists:
                # ! something like match_percentage('rionos', 'aiobahn, rionos Motivation
                # ! (remix)' would return 100, so we're absolutely corrent in matching
                # ! artists to song name.
                if match_percentage(artist.lower(), result['name'].lower(), 85):
                    artistMatchNumber += 1

        # ! Skip if there are no artists in common, (else, results like 'Griffith Swank -
        # ! Madness' will be the top match for 'Ruelle - Madness')
        if artistMatchNumber == 0:
            continue

        artistMatch = (artistMatchNumber / len(songArtists)) * 100

        # Find name match
        nameMatch = round(match_percentage(result['name'], songName), ndigits=3)

        # Find album match
        # ! We assign an arbitrary value of 0 for album match in case of video results
        # ! from YouTube Music
        albumMatch = 0.0

        if result['type'] == 'song':
            albumMatch = match_percentage(result['album'], songAlbumName)

        # Find duration match
        # ! time match = 100 - (delta(duration)**2 / original duration * 100)
        # ! difference in song duration (delta) is usually of the magnitude of a few
        # ! seconds, we need to amplify the delta if it is to have any meaningful impact
        # ! wen we calculate the avg match value
        delta = result['length'] - songDuration
        nonMatchValue = (delta ** 2) / songDuration * 100

        timeMatch = 100 - nonMatchValue

        # the results along with the avg Match
        avgMatch = (artistMatch + albumMatch + nameMatch + timeMatch) / 4

        linksWithMatchValue[result['link']] = avgMatch

    return linksWithMatchValue


def get_ytm_search_query(songName: str, songArtists: List[str]) -> str:
    joined_artists = ', '.join(songArtists)
    return f'{joined_artists} - {songName}'


def search_and_get_best_match(songName: str, songArtists: List[str],
                              songAlbumName: str, songDuration: int) -> typing.Optional[str]:
    '''
    `str` `songName` : name of song

    `list<str>` `songArtists` : list containing name of contributing artists

    `str` `songAlbumName` : name of song's album

    `int` `songDuration` : duration of the song

    RETURNS `str` : link of the best match
    '''

    # ! This is lazy coding, sorry.
    results = search_and_order_ytm_results(
        songName, songArtists,
        songAlbumName, songDuration
    )

    if len(results) == 0:
        return None

    resultItems = list(results.items())
    sortedResults = sorted(resultItems, key=lambda x: x[1], reverse=True)

    # ! In theory, the first 'TUPLE' in sortedResults should have the highest match
    # ! value, we send back only the link
    return sortedResults[0][0]


def get_song_lyrics(song_name: str, song_artists: List[str]) -> str:
    """
    `str` `song_name` : name of song

    `list<str>` `song_artists` : list containing name of contributing artists

    RETURNS `str`: Lyrics of the song.

    Gets the metadata of the song.
    """

    headers = {
        'Authorization': 'Bearer alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG',
    }
    api_search_url = 'https://api.genius.com/search'
    search_query = f'{song_name} {", ".join(song_artists)}'

    api_response = get(
        api_search_url,
        params={'q': search_query},
        headers=headers
    ).json()

    song_id = api_response['response']['hits'][0]['result']['id']
    song_api_url = f'https://api.genius.com/songs/{song_id}'

    api_response = get(
        song_api_url,
        headers=headers
    ).json()

    song_url = api_response['response']['song']['url']

    genius_page = get(song_url)
    soup = BeautifulSoup(genius_page.text, 'html.parser')
    lyrics = soup.select_one('div.lyrics').get_text()

    return lyrics.strip()
