'''
Implementation of the Search interfaces defined in interfaces.md
'''



#===============
#=== Imports ===
#===============
from defaultObjects import metadataObject

from requests import post
from json import loads as convertJsonToDict
from json import dumps as convertDictToJsonStr



#======================
#=== Initialization ===
#======================
ytmApiKey = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'



#========================
#=== Provider Classes ===
#========================
class metadataProvider(object):

    def __init__(self): pass

    def getDetails(self, songObj):
        # The metadata class is the same as the trackDetails class from
        # spotdl.utils.spotifyHelpers.py, it takes a spotify Url as its
        # __init__ arg and implements the metadata object interface over
        # metadata queried from spotify.
        #
        # see also, comment above metadata class declaration in
        # defaultObjects.py
        
        return metadataObject(songObj.getSpotifyLink())
    
    def getLyrics(self, songObj):
        # Not yet implemented, return None as-per the interface rules from
        # interface.md
        return None

class searchProvider(object):
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
    
    def queryAndSimplify(self, searchTerm):
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

        simplifiedResults = {
            'songs' : [],
            'videos': []
        }

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

            # format relevant details
            if availableDetails[1] == 'Song':
                formattedDetails = {
                    'name'      : availableDetails[0],
                    'artist'    : availableDetails[2],
                    'album'     : availableDetails[3],
                    'length'    : availableDetails[4],
                    'link'      : resultLink,
                    'position'  : resultPosition
                }

                if formattedDetails not in simplifiedResults['songs']:
                    simplifiedResults['songs'].append(formattedDetails)
            
            elif availableDetails[1] == 'Video':
                formattedDetails = {
                    'name'      : availableDetails[0],
                    'length'    : availableDetails[4],
                    'link'      : resultLink,
                    'position'  : resultPosition
                }

                if formattedDetails not in simplifiedResults['videos']:
                    simplifiedResults['videos'].append(formattedDetails)
            
            # For things like playlists, albums, etc... just ignore them
            else:
                pass
        
        return simplifiedResults
    
    def save(self):
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
        outFile.write(commentLine)
        outFile.write(formattedResponse)
        outFile.close()