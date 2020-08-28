import requests, json

apiKey = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'

def ytmSearch(query):
    # Prepare post request to YouTube Music
    # The post request was figured out by @rocketinventor (Elliot Gerchak)
    url = "https://music.youtube.com/youtubei/v1/search?alt=json&key=" + apiKey
    
    headers = {
      "Referer": "https://music.youtube.com/search"
      }

    payload = {
      "context": {
        "client": {
          "clientName": "WEB_REMIX",
          "clientVersion": "0.1",
        },
      },
      "query": query
    }

    # Get search results from YouTube Music
    r = requests.post(url,headers=headers, json=payload, stream=True)

    # Convert JSON response to dict-list object for easy processing
    resp = json.loads(r.text)

    # save to file for lookup
    with open(query + '.jsonc', 'w') as file:
        file.write(json.dumps(resp, indent=4, sort_keys=True))

    # Break response into major blocks (Top results, Songs, Videos, Albums,
    # Artists, Playlists, User Notices)
    contentBlocks = resp['contents']['sectionListRenderer']['contents']

    # Get each result from all the blocks, you'd see these as separate row results
    # on YouTube Music
    results = []

    for block in contentBlocks:
        # The 'itemSectionRenderer' field is for user notices ('showing results
        # for xyz, search for abc instead') we have no use for them, the for
        # loop below if throw a keyError if we don't ignore them
        if 'itemSectionRenderer' in block.keys():
            continue

        for each in block['musicShelfRenderer']['contents']:
            detailsBlock = each['musicResponsiveListItemRenderer']['flexColumns']

            if 'overlay' in each['musicResponsiveListItemRenderer']:
                # Add the block containing video / playlist id (which is nested af. as usual)
                detailsBlock.append(each['musicResponsiveListItemRenderer'] \
                    ['overlay'] ['musicItemThumbnailOverlayRenderer']['content'] \
                    ['musicPlayButtonRenderer']['playNavigationEndpoint']
                    )
            
                results.append(detailsBlock)
                
    # Filter out all results that are not Songs or Videos, also
    # select required details from Song and Video results and
    # group them as a dict
    selectResults = {'songs'  : [], 'videos' : []}

    for result in results:
        # gather all details in one place first,
        data = []

        lvOneKey = list(result[-1].keys())[1]           # playlistEndpoint / watchEndpoint
        lvTwoKey = list(result[-1][lvOneKey].keys())[0] # VideoId / playlistId / ...
        linkId = result[-1][lvOneKey][lvTwoKey]         # the bloody link

        for detail in result[:-1]:
            # This blocks out the occasional dummy details, I have no clue as
            # to why the response even contains these things. the below append
            # statement will throw a keyError if we don't ignore these
            if len(detail['musicResponsiveListItemFlexColumnRenderer']) == 1:
                continue

            data.append(detail['musicResponsiveListItemFlexColumnRenderer'] \
                ['text']['runs'][0]['text'])
        
        # now capture relevant details if 'Song' or 'Video', use Position
        # as a fallback for when there are 2+ matches that are equally good.
        position = results.index(result)

        if data[1] == 'Song':
            formattedDetails = {
                'Name'    : data[0],
                'Artist'  : data[2],
                'Album'   : data[3],
                'Length'  : data[4],
                'Link'    : 'https://www.youtube.com/watch?v=' + linkId,
                'Position': position
            }

            if formattedDetails not in selectResults['songs']:
              selectResults['songs'].append(formattedDetails)

        elif data[1] == 'Video':
            formattedDetails = {
                'Name'    : data[0],
                'Length'  : data[4],
                'Link'    : 'https://www.youtube.com/watch?v=' + linkId,
                'Position': position
            }

            if formattedDetails not in selectResults['videos']:
              selectResults['videos'].append(formattedDetails)

        else:
            pass
    
    return selectResults

while True:
    query = input('Search Query: ')

    if query == 'quit()':
        break

    filteredResults = ytmSearch(query)

    print('SONGS:')

    for song in filteredResults['songs']:
        print('%02d.' % song['Position'], end='')
        for detailType, detail in list(song.items())[:-1]:
            print('\t%-10s: %s' % (detailType, detail))
        print('\n')

    print('VIDEOS:')

    for video in filteredResults['videos']:
        print('%02d.' % video['Position'], end='')
        for detailType, detail in list(video.items())[:-1]:
            print('\t%-10s: %s' % (detailType, detail))
        print('\n')