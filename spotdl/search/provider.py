#===============
#=== Imports ===
#===============

#! the following are for the search provider to function
from rapidfuzz.fuzz import partial_ratio
from json import loads as convert_json_to_dict
from requests import post

#! Just for static typing
from typing import List



#================================
#=== Note to readers / Coders ===
#================================

#! YTM search (the actual POST request), courtesy of Elliot G. (@rocketinventor)
#! result parsing and song matching system by @Mikhail-Zex
#!
#! Essentially, Without Elliot, you wouldn't have a YTM search provider at all.



#=======================
#=== helper function ===
#=======================

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

    #! this will throw an error if either string contains a UTF-8 encoded emoji 
    try:
        return partial_ratio(str1, str2, score_cutoff=score_cutoff)

    #! we build new strings that contain only alphanumerical characters and spaces
    #! and return the partial_ratio of that
    except:
        newStr1 = ''

        for eachLetter in str1:
            if eachLetter.isalnum() or eachLetter.isspace():
                newStr1 += eachLetter

        newStr2 = ''

        for eachLetter in str2:
            if eachLetter.isalnum() or eachLetter.isspace():
                newStr2 += eachLetter

        return partial_ratio(newStr1, newStr2, score_cutoff=score_cutoff)

#========================================================================
#=== Background functions/Variables (Not meant to be called directly) ===
#========================================================================

#! as of now there is no need to allow anyone to set a ytm-api key, so no-one should mess
#! with this. It's only defined out here instead of within a class so that chaning of the
#! api key if and when the change happens should be a simple job
ytmApiKey = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'

def __query_and_simplify(searchTerm: str, apiKey: str = ytmApiKey) -> List[dict]:
    #! For dict structure, see end of this function (~ln 268, ln 283) and chill, this
    #! function ain't soo big, there are plenty of comments and blank lines



    # build and POST a query to YTM

    url = 'https://music.youtube.com/youtubei/v1/search?alt=json&key=' + apiKey

    headers = {
        'Referer': 'https://music.youtube.com/search'
    }

    payload = {

        'context': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '0.1'
            }
        },

        'query': searchTerm
    }

    request = post(
        url     = url,
        headers = headers,
        json    = payload
    )
    
    response = convert_json_to_dict(request.text)

    oContents = []

    for content in response['contents']['sectionListRenderer']['contents'][:3]:
        oContents.append(content)

    displayData = []
    for content in oContents:
        displayData += content['musicShelfRenderer']['contents']

    dataDict = {}
    for disp in displayData:
        disp['musicResponsiveListItemRenderer']['flexColumns'][1]['videoId'] = disp['musicResponsiveListItemRenderer']['flexColumns'][0]['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][0]['navigationEndpoint']['watchEndpoint']['videoId']
        dataDict[disp['musicResponsiveListItemRenderer']['flexColumns'][0]['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][0]['text']] = disp['musicResponsiveListItemRenderer']['flexColumns'][1]
    
    simplifiedData = []

    for dataKey in dataDict:
        data = dataDict[dataKey]
        
        sData = {}

            #! For dict structure, see end of this function (~ln 268, ln 283) and chill, this
    #! function ain't soo big, there are plenty of comments and blank lines



    # build and POST a query to YTM

    url = 'https://music.youtube.com/youtubei/v1/search?alt=json&key=' + apiKey

    headers = {
        'Referer': 'https://music.youtube.com/search'
    }

    payload = {

        'context': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '0.1'
            }
        },

        'query': searchTerm
    }

    request = post(
        url     = url,
        headers = headers,
        json    = payload
    )

    open('reand.json','w').write(request.text)
    response = convert_json_to_dict(request.text)

    oContents = []

    for content in response['contents']['sectionListRenderer']['contents'][:3]:
        oContents.append(content)

    displayData = []
    for content in oContents:
        displayData += content['musicShelfRenderer']['contents']

    dataDict = {}
    for disp in displayData:
        disp['musicResponsiveListItemRenderer']['flexColumns'][1]['videoId'] = disp['musicResponsiveListItemRenderer']['flexColumns'][0]['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][0]['navigationEndpoint']['watchEndpoint']['videoId']
        dataDict[disp['musicResponsiveListItemRenderer']['flexColumns'][0]['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][0]['text']] = disp['musicResponsiveListItemRenderer']['flexColumns'][1]
    
    simplifiedData = []

    for dataKey in dataDict:
        data = dataDict[dataKey]
        
        sData = {}

        if data['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][0]['text'] == 'Song':
            sData['name'] = dataKey
            sData['link'] = 'https://www.youtube.com/watch?v=' + data['videoId']

            sData['artist'] = ''
            for possibleArtist in data['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][2:]:
                if possibleArtist['text'].strip().rstrip() == '•':
                    break
                sData['artist'] += possibleArtist['text']   
            
            sData['album'] = data['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][4]['text']

            minStr, secStr = data['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][6]['text'].split(':')

            #! handle leading zeroes (eg. 01, 09, etc...), they cause eval errors, there
            #! are a few oddball tracks that are only a few seconds long
            if minStr[0] == '0' and len(minStr) == 2:
                minStr = minStr[1]
            
            if secStr[0] == '0':
                secStr = secStr[1]
            
            time = int(minStr)*60 + int(secStr)

            sData['length'] = time
            sData['position'] = list(dataDict.keys()).index(dataKey)
            
            simplifiedData.append(sData)
        
        else:
            sData['name'] = dataKey
            sData['link'] = 'https://www.youtube.com/watch?v=' + data['videoId']
            sData['artist'] = data['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][2]['text']
            sData['album'] = None

            minStr, secStr = data['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][6]['text'].split(':')

            #! handle leading zeroes (eg. 01, 09, etc...), they cause eval errors, there
            #! are a few oddball tracks that are only a few seconds long
            if minStr[0] == '0' and len(minStr) == 2:
                minStr = minStr[1]
            
            if secStr[0] == '0':
                secStr = secStr[1]
            
            time = int(minStr)*60 + int(secStr)

            sData['length'] = time
            sData['position'] = list(dataDict.keys()).index(dataKey)
            
            simplifiedData.append(sData)

    # return the results
    return simplifiedData



#=======================
#=== Search Provider ===
#=======================

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

    # Build a YTM search term
    songArtistStr = ''

    for artist in songArtists:
        songArtistStr += artist + ', '
    
    #! the ...[:-2] is so that we don't get the last ', ' of searchStrArtists because we
    #! want $artist1, $artist2, ..., $artistN - $songName
    songSearchStr = songArtistStr[:-2] + ' - ' + songName



    # Query YTM
    results = __query_and_simplify(songSearchStr)



    # Assign an overall avg match value to each result
    linksWithMatchValue = {}

    for result in results:
        #! If there are no common words b/w the spotify and YouTube Music name, the song
        #! is a wrong match (Like Ruelle - Madness being matched to Ruelle - Monster, it
        #! happens without this conditional)
        
        #! most song results on youtube go by $artist - $songName, so if the spotify name
        #! has a '-', this function would return True, a common '-' is hardly a 'common
        #! word', so we get rid of it. Lower-caseing all the inputs is to get rid of the
        #! troubles that arise from pythons handling of differently cased words, i.e.
        #! 'Rhino' == 'rhino' is false though the word is same... so we lower-case both
        #! sentences and replace any hypens(-)
        lowerSongName = songName.lower()
        lowerResultName = result['name'].lower()

        sentenceAWords = lowerSongName.replace('-', ' ').split(' ')
        
        commonWord = False

        #! check for common word
        for word in sentenceAWords:
            if word != '' and word in lowerResultName:
                commonWord = True
        
        #! if there are no common words, skip result
        if not commonWord:
            continue



        # Find artist match
        #! match  = (no of artist names in result) / (no. of artist names on spotify) * 100
        artistMatchNumber = 0

        #! we use fuzzy matching because YouTube spellings might be mucked up:
        for artist in songArtists:
            if match_percentage(artist.lower(), result['artist'].lower(), 85):
                artistMatchNumber += 1
        
        #! Skip if there are no artists in common, (else, results like 'Griffith Swank -
        #! Madness' will be the top match for 'Ruelle - Madness')
        if artistMatchNumber == 0:
            continue
        
        artistMatch = (artistMatchNumber / len(songArtists) ) * 100



        # Find name match
        nameMatch = round(match_percentage(result['name'], songName), ndigits = 3)



        # Find album match
        #! We assign an arbitrary value of 0 for album match in case of video results
        #! from YouTube Music
        albumMatch = 0

        #! result['album'] will be None for a video result
        if result['album']:
            albumMatch = match_percentage(result['album'], songAlbumName)



        # Find duration match
        #! time match = 100 - (delta(duration)**2 / original duration * 100)
        #! difference in song duration (delta) is usually of the magnitude of a few
        #! seconds, we need to amplify the delta if it is to have any meaningful impact
        #! wen we calculate the avg match value
        delta = result['length'] - songDuration
        nonMatchValue = (delta ** 2) / songDuration * 100

        timeMatch = 100 - nonMatchValue



        # the results along with the avg Match
        avgMatch = (artistMatch + albumMatch + nameMatch + timeMatch) / 4

        linksWithMatchValue[result['link']] = avgMatch

    return linksWithMatchValue

def search_and_get_best_match(songName: str, songArtists: List[str],
                                        songAlbumName: str, songDuration: int) -> str:
    '''
    `str` `songName` : name of song
    `list<str>` `songArtists` : list containing name of contributing artists
    `str` `songAlbumName` : name of song's album
    `int` `songDuration` : duration of the song
    RETURNS `str` : link of the best match
    '''

    #! This is lazy coding, sorry.
    results = search_and_order_ytm_results(
        songName, songArtists,
        songAlbumName, songDuration
    )

    if len(results) == 0:
        return None

    resultItems = list(results.items())
    sortedResults = sorted(resultItems, key = lambda x: x[1], reverse=True)

    #! In theory, the first 'TUPLE' in sortedResults should have the highest match
    #! value, we send back only the link
    return sortedResults[0][0]