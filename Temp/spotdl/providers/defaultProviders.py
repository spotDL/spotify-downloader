'''
Implementation of the Search interfaces defined in interfaces.md
'''



#===============
#=== Imports ===
#===============
from spotdl.providers.defaultObjects import songObject
from spotdl.utils.spotifyHelpers import searchForSong

from fuzzywuzzy.fuzz import partial_ratio as matchPercentage

from requests import post

from json import loads as convertJsonToDict
from json import dumps as convertDictToJsonStr



#==================================================
#=== Initialization & Module specific Utilities ===
#==================================================
ytmApiKey = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'

def atLeastOneCommonWord(sentenceA, sentenceB):
    '''

    `str` `sentenceA` : a sentence

    `str` `sentenceB` : another sentence

    returns `True` if there is at least one common word b/w sentenceA and
    sentenceB. It is not case sensitive.
    '''

    # most song results on youtube go by $artist - $songName, so
    # if the spotify name has a '-', this function would return True,
    # a common '-' is hardly a 'common 'word', so we get rid of it.
    # Lower-caseing all the inputs is to get rid of the troubles
    # that arise from pythons handling of differently cased words, i.e.
    # 'Rhino' == 'rhino is false though the word is same...
    lowerSentenceA = sentenceA.lower()
    lowerSentenceB = sentenceB.lower()

    sentenceAWords = lowerSentenceA.replace('-', ' ').split(' ')
    sentenceBWords = lowerSentenceB.replace('-', ' ').split(' ')

    for word in sentenceAWords:
        if word != '' and word in lowerSentenceB:
            return True
    
    for word in sentenceBWords:
        if word != '' and word in lowerSentenceA:
            return True
    
    # The above loops catch common words and return True, thereby exiting the
    # function, if there are no common words, return False
    return False



#========================
#=== Provider Classes ===
#========================
class metadataProvider(object):

    def __init__(self): pass

    def getDetails(self, songObj):
        '''
        `songObj` `songObj` : An object that implements the song object
        interface

        returns an instance of a `metadataObj` containing metadata of the
        song referenced in the `songObj`.
        
        See interfaces.md on github repo for more details
        '''

        # The metadata class is the same as the trackDetails class from
        # spotdl.utils.spotifyHelpers.py, it takes a spotify Url as its
        # __init__ arg and implements the metadata object interface over
        # metadata queried from spotify.
        #
        # see also, comment above metadata class declaration in
        # defaultObjects.py

        # This function is redundant in this implementation, as we again,
        # once more piggyback on trackDetails to get metadata from the
        # Spotify-api. This function is defined to keep in line with the
        # interface definitions. You might say that the interface definition
        # is dumb, maybe true... but, if someone is not satisfied with
        # just the Spotify-api, he/she/them don't have to rewrite the
        # trackDetails class from helpers, they might as well, write their
        # fresh code here, and return an object that implements the metadata
        # object interface, it doesn't even have to be a metadata object, just
        # something that provides the same interface....
        #
        # In case your writing a custom getDetails method,
        #
        #   class customMetadataProvider(metadataProvider):
        #       def getDetails(self, songObj):
        #           # your code goes here
        #           ...
        #
        #           # please apply your metadata to songObj, so the rest of 
        #           # spotDL can benifit from your, fresh/new  metadata
        #           songObj.metadata = yourImplementationOfTheMetadataInterface
        
        return songObj.getMetadata()
    
    def getLyrics(self, songObj):
        '''
        `songObj` `songObj`: Any object that implements the song object
        interface

        returns the lyrics of the referenced song if available, returns
        `None` if no lyrics were found
        '''

        # Not yet implemented, return None as-per the interface rules from
        # interface.md
        return None

class searchProvider(object):
    '''
    Default implementation of the search interface
    
    see interfaces.md for more details
    '''

    # Authored by: Elliot G. (@rocketinventor)
    # Just a few tweaks by @Mikhail-Zex

    def __init__(self, apiKey = ytmApiKey):
        self.url = 'https://music.youtube.com/youtubei/v1/search?alt=json&key=' + apiKey

        self.headers = {
            'Referer': 'https://music.youtube.com/search'
        }

        self.payload = {
            'context': {
                'client': {
                    'clientName': 'WEB_REMIX',
                    'clientVersion': '0.1'
                }
            },

            # Search query to be added here as required by each search
            'query': ''
        }

        # save the response for the current search term if received,
        # not part of the interface, useful for use as a library
        self.cResponse = None

    # The following class methods do all the work

    def queryAndSimplify(self, searchTerm):
        '''
        `str` `searchTerm` : the search term you would type into YouTube
        Music's search bar
        
        queries YouTube Music and simplifies their (as of now) senselessly
        nested JSON response. returns `list<dict>`. Each `dict` has the
        following indices:

        `str` `name` : name of the result as on YouTube Music

        `str` `type` : either 'song' or 'video'
        
        
        `int` `length` : length of result in seconds

        `str` `link` : link of the result on YouTube (not YouTube Music)

        `int` `position` : index of the result from the top of the page (the
        topmost result would be 0)

        The following details will only be present in results with type 'song'

        `str` `artist` : name of artist as on YouTube Music, generally only the
        primary artist
        
        `str` `album` : name of album as on YouTube Music
        '''

        # Query YouTube Music with a POST request, save response to
        # self.cRequest as a dict
        self.payload['query'] = searchTerm

        request = post(
            url=self.url,
            headers=self.headers,
            json=self.payload
        )

        self.cResponse = convertJsonToDict(request.text)

        # We will hereon call generic levels of nesting as 'Blocks'
        # An overview of the basic nesting (you'll need it),

        # Content blocks
        #       Group results into 'Top result', 'Songs', 'Videos',
        #       'playlists', 'Albums', 'User notices', etc...
        #
        # Result blocks (under each 'Content block')
        #       Represents an individual song, album, video, playlist
        #       result, etc...
        #
        # Detail blocks (under each 'Result block')
        #       Represents a detail of the result, these might be one of
        #       name, duration, channel, album, etc...
        #
        # Link block (under each 'Result block')
        #       Contains the video/Album/playlist/Song/Artist link of the
        #       result as found on YouTube

        # Simplify the senselessly nested YTM response, nested-dict keys are
        # used to (a) indicate nesting visually, (b) make the code more
        # readable

        # Break response into content blocks
        contentBlocks = self.cResponse['contents'] \
            ['sectionListRenderer'] \
                ['contents']
        
        # Gather all results from all content blocks in the same place
        resultBlocks = []

        for block in contentBlocks:
            # The 'itemSectionRenderer' field is for user notices (stuff like -
            # 'showing results for xyz, search for abc instead') we have no
            # use for them, the for loop below if throw a keyError if we don't
            # ignore them
            if 'itemSectionRenderer' in block.keys():
                continue

            for result in block['musicShelfRenderer']['contents']:
                detailsBlock = result['musicResponsiveListItemRenderer'] \
                    ['flexColumns']
                
                if 'overlay' in result['musicResponsiveListItemRenderer']:
                    linkBlock = result['musicResponsiveListItemRenderer'] \
                        ['overlay'] \
                        ['musicItemThumbnailOverlayRenderer'] \
                            ['content'] \
                                ['musicPlayButtonRenderer'] \
                                    ['playNavigationEndpoint']
                
                # detailsBlock is always a list, so we just append the
                # linkBlock to it insted of carrying along all the other
                # junk from 'musicResponsiveListItemRenderer'
                detailsBlock.append(linkBlock)

                resultBlocks.append(detailsBlock)
        
        # We only need results that are Songs or Videos, so we filter out the
        # rest, since Songs and Videos are supplied with different details,
        # extracting all details from both is just carrying on redundant data,
        # So we also have to selectively extract relevant details. What you
        # need to know to understand how we do that here:
        #
        # Songs details are ALWAYS in the following order:
        #       0 - Name
        #       1 - Type (Song)
        #       2 - Artist
        #       3 - Album
        #       4 - Duration (mm:ss)
        #
        # Video details are ALWAYS in the following order:
        #       0 - Name
        #       1 - Type (Video)
        #       2 - Channel
        #       3 - Viewers
        #       4 - Duration (hh:mm:ss)
        #
        # We blindly gather all the details we get our hands on, then
        # cherrypick the details we need based on  their index numbers,
        # we do so only if their Type is 'Song' or 'Video

        simplifiedResults = []

        for result in resultBlocks:
            # Blindly gather all available details
            availableDetails = []

            # Remember that we appended the linkBlock to result, treating that
            # like the other constituents of a result block will lead to errors,
            # hence the 'in result[:-1]'
            for detail in result[:-1]:

                # 'musicResponsiveListItmeFlexColumnRenderer' should have more that
                # one sub-block, if not its a dummy, why does the YTM response
                # contain dummies? I have no clue. We skip these
                if len(detail['musicResponsiveListItemFlexColumnRenderer']) < 2:
                    continue

                # if not a dummy, collect all available details
                availableDetails.append(
                    detail['musicResponsiveListItemFlexColumnRenderer'] \
                        ['text'] \
                            ['runs'][0] \
                                ['text']
                )
        
            # Now filter out non-Song/Video results while capturing relevant
            # details for song/video results. From what we know about detail order,
            # note that [1] - indicate result type
            if availableDetails[1] in ['Song', 'Video']:
                # skip result if length is in hours or seconds (i.e. not in mins),
                # time is formatted as hh:mm:ss
                if len(availableDetails[4].split(':')) != 2:
                    continue

                # grab position of result in the response for the odd-ball cases
                # when 2+ results seem to be equally good, in such a case the
                # result higher up in the results can be taken as the better match
                resultPosition = resultBlocks.index(result)

                # grab the link of the result too, this is nested as
                # [playlistEndpoint/watchEndpoint][videoId/playlistId/etc...], so
                # hardcoding the dict keys for data look up is an ardours process,
                # since the sub-block pattern is fixed even though the key isn't,
                # we just reference the dict keys by index
                endpointKey = list( result[-1].keys() )[1]
                resultIdKey = list( result[-1][endpointKey].keys() )[0]

                linkId = result[-1][endpointKey][resultIdKey]
                resultLink = 'https://www.youtube.com/watch?v=' + linkId

                # convert length to seconds
                minStr, secStr = availableDetails[4].split(':')

                # handle leading zeroes (eg. 01, 09, etc...), they cause
                # eval errors
                if minStr[0] == '0':
                    minStr = minStr[1]
                if secStr[0] == '0':
                    secStr = secStr[1]
                
                time = eval(minStr) + eval(secStr)

                # format relevant details
                if availableDetails[1] == 'Song':
                    formattedDetails = {
                        'name'      : availableDetails[0],
                        'type'      : 'song',
                        'artist'    : availableDetails[2],
                        'album'     : availableDetails[3],
                        'length'    : time,
                        'link'      : resultLink,
                        'position'  : resultPosition
                    }

                    if formattedDetails not in simplifiedResults:
                        simplifiedResults.append(formattedDetails)

                elif availableDetails[1] == 'Video':
                    formattedDetails = {
                        'name'      : availableDetails[0],
                        'type'      : 'video',
                        'length'    : time,
                        'link'      : resultLink,
                        'position'  : resultPosition
                    }

                    if formattedDetails not in simplifiedResults:
                        simplifiedResults.append(formattedDetails)

                # For things like playlists, albums, etc... just ignore them
                else:
                    pass
                
        return simplifiedResults
    
    def searchAndFilterYTM(self, songDetails, getBestMatchOnly = False):
        '''
        `metadataObj` `songDetails` : metadata of the song to be matched
        
        `bool` `getBestMatchOnly` : decides to return top result or all results

        First query's YouTube Music via the queryAndSimplify method, then
        matches the provided results agains the metadata from `songDetails`. It
        adds a 'avgMatch' index to each result provided by queryAndSimplify indicating
        the % similarity the result has with the given metadata.

        returns all results with the additional 'avgMatch' field or only the result
        with the best overall match depending on `getBestMatchOnly`
        '''

        # Build a youtube search term
        searchTerm = ''

        for artist in songDetails.getContributingArtists():
            searchTerm += artist + ', '
        
        # ..[:-2] is because we don't want the last ', '
        searchTerm = searchTerm[:-2] + ' - ' + songDetails.getSongName()

        # Get YouTube Music Results
        results = self.queryAndSimplify(searchTerm)

        # This list gathers all the processed/filtered results
        filteredResults = []

        for result in results:
            # If there are no common words b/w the spotify and YouTube Music
            # name, the song is a wrong match (Like Ruelle - Madness being
            # matched to Ruelle - Monster, it happens without this conditional)
            if not atLeastOneCommonWord(songDetails.getSongName(), result['name']):
                continue

            # Find artists match %
            artistMatch = 0

            if result['type'] == 'song':
                for artist in songDetails.getContributingArtists():
                    if artist.lower() in result['artist'].lower():
                        artistMatch += 1
            else:
                for artist in songDetails.getContributingArtists():
                    if artist.lower() in result['name'].lower():
                        artistMatch += 1
            
            artistMatchRatio = artistMatch/len(songDetails.getContributingArtists())
            artistMatchPercentage = artistMatchRatio * 100

            # Skip if there are no artists in common, (else, results like
            # 'Leven - Madness' will be the top match for 'Ruelle - Madness')
            if artistMatchPercentage == 0:
                continue

            # Find name match%
            nameMatchPercentage = matchPercentage(
                result['name'],
                songDetails.getSongName()
            )

            # Find album name match %, 0 is the default, it is used in case of
            # video results from YouTube Music
            albumMatchPercentage = 0

            if result['type'] == 'song':
                albumMatchPercentage = matchPercentage(
                    result['album'],
                    songDetails.getAlbumName()
                )
            
            # Add an average match percentage to result
            avgMatch = (artistMatchPercentage + albumMatchPercentage
                + nameMatchPercentage) / 3
               
            result['avgMatch'] = avgMatch
               
            filteredResults.append(result)
        
        if getBestMatchOnly:
            # If we are to return only the top result after filtering
            topResult = None

            for result in filteredResults:
                if result['avgMatch'] > topResult['avgMatch']:
                    topResult = result
                elif result['avgMatch'] == topResult['avgMatch']:
                    if result['position'] < topResult['position']:
                        topResult = result
            
            return topResult

        else:
            # If we are to return all results
            return filteredResults

    # save is a little utility in case you want to study YouTube Music's JSON
    # responses, they are quite messy. Not used within spotDL, but might
    # be of use, when using spotDL as a library

    def save(self):
        '''
        saves the YouTube Music Query Response as-is to a .jsonc file in
        the directory of execution
        '''

        # save the details of the latest YTM query as-is to query.jsonc
        latestQuery = self.payload['query']

        # we open file as 'wb' to accommodate the existence of non english
        # character in the response (like you'd get if you searched for a 
        # japanese song)
        commentLine = '//YouTube Music Response for query "%s"\n\n' % latestQuery
        formattedResponse = convertDictToJsonStr(
            self.cResponse,
            indent=4,
            sort_keys=True
        )

        outFile = open(latestQuery + '.jsonc', 'wb')
        outFile.write(commentLine.encode())
        outFile.write(formattedResponse.encode())
        outFile.close()

    # The class methods below are interface implimentations, if you intend to
    # understand how they work, go through the methods defined above, thats
    # where the real work is
    
    def searchFromName(self, query):
        '''
        `str` `query` : search query you would type into Spotify's search box

        returns the best match to the given search query as a `songObj`
        '''

        # Search for the best match and get the song's details
        songSpotifyUrl = searchForSong(query)
        songDetails = metadataObject(songSpotifyUrl)

        # Find matches from YouTube Music
        result = self.searchAndFilterYTM(songDetails, getBestMatchOnly = True)

        resultAsSongObj = songObject(
            name = result['name'],

            # MetadataObject is more complete than YouTube Music results
            artists = songDetails.getContributingArtists(),
            
            sLen = songDetails.getLength(),
            yLen = result['length'],
            
            sLink = songSpotifyUrl,
            yLink = result['link'],
            
            metadata = songDetails
        )

        return resultAsSongObj
    
    def searchFromUrl(self, url):
        '''
        `str` `url` : Spotify Url of song to be matched on YouTube Music

        returns best overall match as a `songObj`
        '''

        songDetails = metadataObject(url)

        # Find matches from YouTube Music
        result = self.searchAndFilterYTM(songDetails, getBestMatchOnly = True)

        resultAsSongObj = songObject(
            name = result['name'],

            # MetadataObject is more complete than YouTube Music results
            artists = songDetails.getContributingArtists(),
            
            sLen = songDetails.getLength(),
            yLen = result['length'],
            
            sLink = url,
            yLink = result['link'],
            
            metadata = songDetails
        )

        return resultAsSongObj
    
    def searchAllFromName(self, query):
        '''
        `str` `query` : search query you would type into Spotify's search box

        returns the all matches to the given search query as a `list<songObj>`
        '''

        # Search for the best match and get the song's details
        songSpotifyUrl = searchForSong(query)
        songDetails = metadataObject(songSpotifyUrl)

        # Find matches from YouTube Music
        results = self.searchAndFilterYTM(songDetails, getBestMatchOnly = False)

        allResults = []

        for result in results:
            resultAsSongObj = songObject(
                name = result['name'],

                # MetadataObject is more complete than YouTube Music results
                artists = songDetails.getContributingArtists(),

                sLen = songDetails.getLength(),
                yLen = result['length'],

                sLink = songSpotifyUrl,
                yLink = result['link'],

                metadata = songDetails
            )

            allResults.append(resultAsSongObj)

        return allResults

    def searchAllFromUrl(self, url):
        '''
        `str` `url` : Spotify url of the song to be matched on YouTube Music

        returns the all matches to the given search query as a `list<songObj>`
        '''

        # Search for the best match and get the song's details
        songDetails = metadataObject(url)

        # Find matches from YouTube Music
        results = self.searchAndFilterYTM(songDetails, getBestMatchOnly = False)

        allResults = []

        for result in results:
            resultAsSongObj = songObject(
                name = result['name'],

                # MetadataObject is more complete than YouTube Music results
                artists = songDetails.getContributingArtists(),

                sLen = songDetails.getLength(),
                yLen = result['length'],

                sLink = url,
                yLink = result['link'],

                metadata = songDetails
            )

            allResults.append(resultAsSongObj)

        return allResults