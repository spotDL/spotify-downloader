import re
from html import unescape

from requests import get


def get_lyrics(songName: str, artistName: str) -> str:
    '''
    `str` `songName`   : Name of the song
    `str` `artistName` : Name of the primary artist

    RETURNS `str` : lyrics of the song
    '''

    # ! used try, except just in case genius doesn't return any results.
    try:

        # ! Access Token for genius api.
        geniusHeaders = {
            'Authorization':
                'Bearer alXXDbPZtK1m2RrZ8I4k2Hn8Ahsd0Gh_o076HYvcdlBvmc0ULL1H8Z8xRlew5qaG',
        }

        # ! We can't send a search query seperated with spaces.
        # ! So, we seperate song name and artist name using '+' instead of spaces (' ')
        query = '+'.join((songName + artistName).split(' '))

        # ! Base url for a search query.
        searchURL = 'https://api.genius.com/search'

        # ! Get Search response from Genius.
        geniusResponse = get(
            searchURL,
            headers=geniusHeaders,
            params={'q': query}
        ).json()

        # ! Take only the response, leave the status_code.
        geniusResponse = geniusResponse['response']

        # ! We select the best match that genius provides, i.e, the first one.
        # ! Gets the songID of the best match from the genius response
        # ! The song id is actually an int so we've to convert it to a string.
        bestMatchID = str(geniusResponse['hits'][0]['result']['id'])

        # ! and then uses that to get it's URL.
        bestMatchURL = 'https://api.genius.com/songs/' + bestMatchID

        # ! Gets the lyrics page url from genius' response.
        songURL = get(
            bestMatchURL,
            headers=geniusHeaders
        ).json()['response']['song']['url']

        # ! Compile All the required Regular Expressions.
        # ! Matches the lyrics.( including html tags)
        lyricsRegex = re.compile(r'<div class="Lyrics__Container.*?>.*</div><div class="RightSidebar.*?>')

        # ! Matches HTML tags.
        htmlTagRegex = re.compile(r'<.*?>')

        # ! Matches Genius Tags like [Chorus]
        genTagRegex = re.compile(r'\[.*?\]', re.DOTALL)

        # ! we use this regex to handle egde cases: (\n Some_lyric \n) -> (Some_Lyric)
        edgeRegEx = re.compile(r'(\()(\n)(.*?)(\n)(\))')

        # ! Gets the genius lyrics page.
        geniusPage = get(songURL).text

        # ! Takes the first string that matches lyricsRegex
        preLyrics = re.findall(lyricsRegex, geniusPage)[0]

        # ! Substitutes HTML Tags for newline characters.
        preLyrics = htmlTagRegex.sub('\n', preLyrics)

        # ! Replace Multiple Newline characters by a single newline character.
        lyrics = []
        for i in preLyrics.split('\n'):
            if i != '\n' and i:
                lyrics.append(i)

        lyrics = "\n".join(lyrics)

        # ! Replaces all HTML escaped characters with unescaped characters.
        lyrics = unescape(lyrics)

        # ! Substitute genius tags for newlines.
        lyrics = genTagRegex.sub('\n', lyrics)
        lyrics = edgeRegEx.sub(r'\1\3\5', lyrics)  # ! Edge case handling
    except:
        lyrics = ''

    # ! Removes trailing and leading newlines and spaces.
    return lyrics.strip()
