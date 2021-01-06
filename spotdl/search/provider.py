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
    '''
    `str` `searchTerm` : the search term you would type into YTM's search bar

    RETURNS `list<dict>`

    For structure of dict, see comment at function declaration
    '''

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

    #! We will hereon call generic levels of nesting as 'Blocks'. What follows is an
    #! overview of the basic nesting (you'll need it),
    #!
    #! Content blocks
    #!       Group results into 'Top result', 'Songs', 'Videos',
    #!       'playlists', 'Albums', 'User notices', etc...
    #!
    #! Result blocks (under each 'Content block')
    #!       Represents an individual song, album, video, ..., playlist
    #!       result
    #!
    #! Detail blocks (under each 'Result block')
    #!       Represents a detail of the result, these might be one of
    #!       name, duration, channel, album, etc...
    #!
    #! Link block (under each 'Result block')
    #!       Contains the video/Album/playlist/Song/Artist link of the
    #!       result as found on YouTube
    
    # Simplify and extract necessary details from senselessly nested YTM response
    #! This process is broken into numbered steps below

    #! nested-dict keys are used to (a) indicate nesting visually and (b) make the code
    #! more readable



    # 01. Break response into contentBLocks
    contentBlocks = response['contents'] \
        ['sectionListRenderer'] \
            ['contents']



    # 02. Gather all result block in the same place
    resultBlocks = []

    for cBlock in contentBlocks:
        # Ignore user-suggestion

        #! The 'itemSectionRenderer' field is for user notices (stuff like - 'showing
        #! results for xyz, search for abc instead') we have no use for them, the for
        #! loop below if throw a keyError if we don't ignore them
        if 'itemSectionRenderer' in cBlock.keys():
            continue

        for contents in cBlock['musicShelfRenderer']['contents']:
            #! apparently content Blocks without an 'overlay' field don't have linkBlocks
            #! I have no clue what they are and why there even exist
            if 'overlay' not in contents['musicResponsiveListItemRenderer']:
                continue

            result = contents['musicResponsiveListItemRenderer'] \
                ['flexColumns']
            


            # Add the linkBlock        
            
            linkBlock = contents['musicResponsiveListItemRenderer'] \
                ['overlay'] \
                    ['musicItemThumbnailOverlayRenderer'] \
                        ['content'] \
                            ['musicPlayButtonRenderer'] \
                                ['playNavigationEndpoint']
            
            #! detailsBlock is always a list, so we just append the linkBlock to it
            #! insted of carrying along all the other junk from 'musicResponsiveListItemRenderer'
            result.append(linkBlock)
        
            #! gather resultBlock
            resultBlocks.append(result)
    
    

    # 03. Gather available details in the same place

    #! We only need results that are Songs or Videos, so we filter out the rest, since
    #! Songs and Videos are supplied with different details, extracting all details from
    #! both is just carrying on redundant data, so we also have to selectively extract
    #! relevant details. What you need to know to understand how we do that here:
    #!
    #! Songs details are ALWAYS in the following order:
    #!       0 - Name
    #!       1 - Type (Song)
    #!       2 - Artist
    #!       3 - Album
    #!       4 - Duration (mm:ss)
    #!
    #! Video details are ALWAYS in the following order:
    #!       0 - Name
    #!       1 - Type (Video)
    #!       2 - Channel
    #!       3 - Viewers
    #!       4 - Duration (hh:mm:ss)
    #!
    #! We blindly gather all the details we get our hands on, then
    #! cherrypick the details we need based on  their index numbers,
    #! we do so only if their Type is 'Song' or 'Video

    simplifiedResults = []

    for result in resultBlocks:

        # Blindly gather available details
        availableDetails = {}

        availableDetails['name'] = result[0]['musicResponsiveListItemFlexColumnRenderer']['text']['runs'][0]['text']
        remainingDetailContainer = result[1]['musicResponsiveListItemFlexColumnRenderer']['text']['runs']
        availableDetails['type'] = remainingDetailContainer[0]['text']

        # Filterout non-Song/Video results and incomplete results here itself
        if availableDetails['type'] in ['Song', 'Video']:
            
            if availableDetails['type'] == 'Song':
                availableDetails['artist'] = remainingDetailContainer[2]['text']
                availableDetails['album'] = remainingDetailContainer[4]['text']

            availableDetails['time'] = remainingDetailContainer[6]['text']

            #! skip if result is in hours instead of minuts (no song is that long)
            if len(availableDetails['time'].split(':')) != 2:
                continue



            # grab position of result
            #! This helps for those oddball cases where 2+ results are rated equally,
            #! lower position --> better match
            resultPosition = resultBlocks.index(result)



            # grab result link
            #! this is nested as [playlistEndpoint/watchEndpoint][videoId/playlistId/...]
            #! so hardcoding the dict keys for data look up is an ardours process, since
            #! the sub-block pattern is fixed even though the key isn't, we just
            #! reference the dict keys by index
            endpointKey = list( result[-1].keys() )[1]
            resultIdKey = list( result[-1][endpointKey].keys() )[0]

            linkId = result[-1][endpointKey][resultIdKey]
            resultLink = 'https://www.youtube.com/watch?v=' + linkId



            # convert length into seconds
            minStr, secStr = availableDetails['time'].split(':')

            #! handle leading zeroes (eg. 01, 09, etc...), they cause eval errors, there
            #! are a few oddball tracks that are only a few seconds long
            if minStr[0] == '0' and len(minStr) == 2:
                minStr = minStr[1]
            
            if secStr[0] == '0':
                secStr = secStr[1]
            
            time = eval(minStr)*60 + eval(secStr)



            # format relevant details
            if availableDetails['type'] == 'Song':
                formattedDetails = {
                    'name'      : availableDetails['name'],
                    'type'      : 'song',
                    'artist'    : availableDetails['artist'],
                    'album'     : availableDetails['album'],
                    'length'    : time,
                    'link'      : resultLink,
                    'position'  : resultPosition
                }
            
                if formattedDetails not in simplifiedResults:
                    simplifiedResults.append(formattedDetails)
            
            elif availableDetails['type'] == 'Video':
            
                formattedDetails = {
                    'name'      : availableDetails['name'],
                    'type'      : 'video',
                    'length'    : time,
                    'link'      : resultLink,
                    'position'  : resultPosition
                }
            
                if formattedDetails not in simplifiedResults:
                    simplifiedResults.append(formattedDetails)
            
            #! Things like playlists, albums, etc... just get ignored
            


    # return the results
    return simplifiedResults



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

        #! we use fuzzy matching because YouTube spellings might be mucked up
        if result['type'] == 'song':
            for artist in songArtists:
                if match_percentage (artist.lower(), result['artist'].lower(), 85):
                    artistMatchNumber += 1
        else:
            #! i.e if video
            for artist in songArtists:
                #! something like match_percentage('rionos', 'aiobahn, rionos Motivation
                #! (remix)' would return 100, so we're absolutely corrent in matching
                #! artists to song name.
                if match_percentage(artist.lower(), result['name'].lower(), 85):
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

        if result['type'] == 'song':
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
