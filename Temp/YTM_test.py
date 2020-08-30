from requests import post
from fuzzywuzzy import fuzz

from datetime import datetime

from spotdl.utils.authorization import getSpotifyClient
spotify_client_id = "4fe3fecfe5334023a1472516cc99d805"
spotify_client_secret = "0f02b7c483c04257984695007a4a8d5c"

getSpotifyClient(
    clientId=spotify_client_id,
    clientSecret=spotify_client_secret
)

from spotdl.utils.spotifyHelpers import searchForSong, trackDetails
from spotdl.providers.defaultObjects import songObject, metadataObject

from json import loads as convertJsonToDict
from json import dumps as convertDictToJsonStr

ytmApiKey = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'

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
        outFile.write(commentLine.encode())
        outFile.write(formattedResponse.encode())
        outFile.close()

    def searchFromName(self, name):
        topRes = (0,'')

        songUrl = searchForSong(name)
        song = trackDetails(songUrl)

        print(song.getSongName())
#        print(song.getContributingArtists())
#        print(song.getAlbumName())
#        print(song.getLength())
#        print()

        searchTerm = ''
        for artist in song.getContributingArtists():
            searchTerm += artist + ', '
        
        searchTerm = searchTerm[:-2] + ' - ' + song.getSongName()

        result = self.queryAndSimplify(searchTerm)

        for each in result['songs'] + result['videos']:
            w = 0
            q = 0

#            print(song.getSongName())
#            print(each['name'])
            q = fuzz.ratio(
                song.getSongName(),
                each['name']
            )

            nameMatch = False
            rop = song.getSongName().lower().split(' ')
            for _ in rop:
                if _ in each['name']:
                    nameMatch = True
                    break
            
            rop = each['name'].lower().split(' ')
            for _ in rop:
                if _ in each['name']:
                    nameMatch = True
                    break

#            print(q)
#            print()

            e = 0

            if each in result['songs']:
                for artist in song.getContributingArtists():
                    if artist.lower() in each['artist'].lower():
                        e += 1
            else:
                for artist in song.getContributingArtists():
                    if artist.lower() in each['name'].lower():
                        e += 1
            
            r = e/len(song.getContributingArtists())
            r = r*100

            _ = song.getContributingArtists()
            popqro = ''

#            print(song.getAlbumName())
            try:
#                print(each['album'])
                w = fuzz.ratio(
                song.getAlbumName(),
                each['album']
                )
#                print(w)
            except:
                pass
#                print('Video Result')
            
#            print()
            if r != 0 and nameMatch:
                z = (q + w + r)/3
                if z > topRes[0]:
                    topRes = (z, each)
                elif z == topRes[0]:
                    if each['position'] < topRes[1]['position']:
                        topRes = (z, each)

        print('---------------------------------------------------------------------')
        print(topRes[1]['name'])
        try:
            print(topRes[1]['artist'])
        except:pass
        print(topRes[1]['link'])
        print('MATCH AVG: %f' % topRes[0])

        return result

q = searchProvider()

while True:
    query = input('\nSearch Query: ')

    if query == 'quit()':
        break

    t1 = datetime.now()
    q.searchFromName(query)
    t2 = datetime.now()

    print(t2-t1)

#while True:
#    query = input('search query: ')
#
#    if query == 'quit()':
#        break
#
#    filteredResults = q.searchFromName(query)
#    q.save()
#
#    print('Results for %s:\n' % query)
#    print('SONGS:')
#
#    for song in filteredResults['songs']:
#        print('%02d.' % song['position'], end='')
#        for detailType, detail in list(song.items())[:-1]:
#            print('\t%-10s: %s' % (detailType, detail))
#        print('\n')
#
#    print('VIDEOS:')
#
#    for video in filteredResults['videos']:
#        print('%02d.' % video['position'], end='')
#        for detailType, detail in list(video.items())[:-1]:
#            print('\t%-10s: %s' % (detailType, detail))
#        print('\n')