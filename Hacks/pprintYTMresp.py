from json import loads

def ytmSearch(fileName):
    file = open(fileName + '.txt', 'rb')
    resp = eval(file.read().decode().replace('false', 'False').replace('true', 'True'))
    file.close()

    # Break response into major blocks (Top results, Songs, Videos, Albums,
    # Artists, Playlists)
    contentBlocks = resp['contents']['sectionListRenderer']['contents']

    # Get each result from all the blocks, you'd see these as separate row results
    # on YouTube Music
    results = []

    for block in contentBlocks:
        # The itemSectionRenderer field is for user notices ('showing results
        # for xyz, search for abc instead') we have no use for them, the for
        # loop below if throw a keyError if we don't ignore them
        if 'itemSectionRenderer' in block.keys():
            continue

        for each in block['musicShelfRenderer']['contents']:
            results.append(each['musicResponsiveListItemRenderer']['flexColumns'])
    
    # Filter out all results that are not Songs or Videos
    selectResults = {'songs'  : [], 'videos' : []}

    for result in results:
        # gather all details in one place first,
        data = []

        for detail in result:
            # This blocks out the occasional dummy details, I have no clue as
            # to why the response even contains these things. the below append
            # statement will throw a keyError if we don't ignore these
            if len(detail['musicResponsiveListItemFlexColumnRenderer']) == 1:
                continue

            data.append(detail['musicResponsiveListItemFlexColumnRenderer'] \
                ['text']['runs'][0]['text'])
        
        # now capture relevant details if 'Song' or 'Video', use Position
        # as a fallback whe there are 2+ matches that are equally good.
        position = results.index(result)

        if data[1] == 'Song':
            formattedDetails = {
                'Name'    : data[0],
                'Artist'  : data[2],
                'Album'   : data[3],
                'Length'  : data[4],
                'Position': position
            }

            if formattedDetails not in selectResults['songs']:
              selectResults['songs'].append(formattedDetails)

        elif data[1] == 'Video':
            formattedDetails = {
                'Name'    : data[0],
                'Length'  : data[4],
                'Position': position
            }

            if formattedDetails not in selectResults['videos']:
              selectResults['videos'].append(formattedDetails)

        else:
            pass

    print('SONGS:')
    for song in selectResults['songs']:
        print('%02d.' % song['Position'], end='')

        for detailType, detail in list(song.items())[:-1]:
            print('\t%-10s: %s' % (detailType, detail))
        print('\n')

    print('VIDEOS:')
    for video in selectResults['videos']:
        print('%02d.' % video['Position'], end='')

        for detailType, detail in list(video.items())[:-1]:
            print('\t%-10s: %s' % (detailType, detail))
        print('\n')

file = [
    'Aiobahn ここにいる',
    'Old gods of asgard Take Control',
    'Ira Ivory Rasmus',
    'Sankarin Tango',
    'The Beat Spinning records'
]

for _ in file:
    ytmSearch(_)

# Output is as follows
#
# SONGS:
# 01.     Name      : ここにいる (feat. rionos)
#         Artist    : Aiobahn
#         Album     : ここにいる
#         Length    : 4:10
# 
# 
# 02.     Name      : ここにいる (Stephen Walking Remix) (feat. rionos)
#         Artist    : Aiobahn
#         Album     : ここにいる (The Remixes)
#         Length    : 3:51
# 
# 
# 03.     Name      : ここにいる (Aire Remix) (feat. rionos)
#         Artist    : Aiobahn
#         Album     : ここにいる (The Remixes)
#         Length    : 3:36
# 
# 
# VIDEOS:
# 00.     Name      : Aiobahn - ここにいる (I'm Here) (feat. rionos) [Official Audio / YouTube Ver.]
#         Length    : 3:43
# 
# 
# 05.     Name      : Aiobahn feat. rionos - ここにいる (I'm Here) (Stephen Walking Remix) [CC]
#         Length    : 3:52
# 
# 
# 06.     Name      : Aiobahn - ここにいる (I'm Here) (feat. rionos) [Stephen Walking Remix / Official Audio]
#         Length    : 3:51
# 
# 
# SONGS:
# 01.     Name      : Take Control
#         Artist    : Old Gods of Asgard
#         Album     : Take Control
#         Length    : 7:53
# 
# 
# 02.     Name      : Children of the Elder God
#         Artist    : Old Gods of Asgard
#         Album     : Memory Thought Balance Ruin
#         Length    : 3:40
# 
# 
# 03.     Name      : Balance Slays the Demon
#         Artist    : Old Gods of Asgard
#         Album     : Balance Slays the Demon
#         Length    : 5:14
# 
# 
# VIDEOS:
# 00.     Name      : Old Gods of Asgard - Take Control (Lyric Video)
#         Length    : 7:58
# 
# 
# 05.     Name      : Old Gods Of Asgard - Take Control (from 'Control' OST)
#         Length    : 7:55
# 
# 
# 06.     Name      : Old Gods of Asgard | Take Control (Solo Cover)
#         Length    : 1:41
# 
# 
# SONGS:
# 00.     Name      : Ira
#         Artist    : Ivory Rasmus
#         Album     : Ira
#         Length    : 3:04
# 
# 
# 01.     Name      : Ira
#         Artist    : Ivory Rasmus
#         Album     : Ira
#         Length    : 3:04
# 
# 
# 02.     Name      : What I've Become
#         Artist    : Ivory Rasmus
#         Album     : What I've Become
#         Length    : 2:32
# 
# 
# 03.     Name      : Not Holding Back
#         Artist    : Ivory Rasmus
#         Album     : Not Holding Back
#         Length    : 2:47
# 
# 
# VIDEOS:
# 04.     Name      : Ira (From Lord Bungs Confinement Series) By Ivory Rasmus
#         Length    : 3:06
# 
# 
# 05.     Name      : ivory rasmus - ira
#         Length    : 3:06
# 
# 
# 06.     Name      : Confinement - Let Me Be Alive - Ivory Rasmus
#         Length    : 2:35
# 
# 
# SONGS:
# 01.     Name      : Satumaa (Finnish Tango) (Live / Helsinki, Finland / 1974)
#         Artist    : Frank Zappa
#         Album     : You Can't Do That On Stage Anymore, Vol. 2 - The Helsinki Concert
#         Length    : 3:52
# 
# 
# 02.     Name      : Take Control
#         Artist    : Old Gods of Asgard
#         Album     : Take Control
#         Length    : 7:53
# 
# 
# 03.     Name      : Tango Fight
#         Artist    : Bear McCreary
#         Album     : Human Target: Season 1 (Original Television Soundtrack)
#         Length    : 1:27
# 
# 
# VIDEOS:
# 00.     Name      : OST Control - Sankarin Tango (Finnish Tango)
#         Length    : 3:20
# 
# 
# 05.     Name      : Sankarin Tango [Control] - Jan Simons (Game Awards 2019)
#         Length    : 0:33
# 
# 
# 06.     Name      : Martti Suosalo - Sankarin Tango (Hero's Tango) Live Studio Version
#         Length    : 3:09
# 
# 
# SONGS:
# 04.     Name      : My Best Life (feat. Mike Waters)
#         Artist    : KSHMR
#         Album     : My Best Life
#         Length    : 3:32
# 
# 
# 05.     Name      : Perfect [LUM!X Remix] (feat. Haris)
#         Artist    : Lucas & Steve
#         Album     : Perfect [LUM!X Remix]
#         Length    : 3:07
# 
# 
# 06.     Name      : Good
#         Artist    : LODATO
#         Album     : Good
#         Length    : 3:32
# 
# 
# VIDEOS:
# 07.     Name      : Spinnin’ Records - Best of 2019 Year Mix
#         Length    : 3:06:45
# 
# 
# 08.     Name      : Spinnin' Records - Best Of 2015 Year Mix
#         Length    : 2:32:47
# 
# 
# 09.     Name      : Spinnin' Records - Best Of 2016 Year Mix
#         Length    : 1:37:01