from datetime import datetime

from spotdl.utils.authorization import getSpotifyClient
spotify_client_id = "4fe3fecfe5334023a1472516cc99d805"
spotify_client_secret = "0f02b7c483c04257984695007a4a8d5c"

getSpotifyClient(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
)


from spotdl.providers.defaultProviders import searchProvider

ytmApiKey = 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30'

q = searchProvider()

# print('-----------------------------------------------------------------------------')
# 
# w = q.searchFromName('assassins creed valhalla main theme')
# print('query: assassins creed valhalla main theme')
# print('-----------------------------------------------------------------------------')
# print(w.getSongName())
# print(w.getYoutubeLink())
# print()
# 
# w1 = q.searchAllFromName('Aiobahn, rionos Stephen Walking remix')
# print('query: Aiobahn, rionos Stephen Walking remix')
# print('-----------------------------------------------------------------------------')
# for w in w1:
#     print(w.getSongName())
#     print(w.getYoutubeLink())
#     print()
# 
# w = q.searchFromUrl('https://open.spotify.com/track/77rj41HJ2iSYuJYdcsucFq?si=-NqSPaB8Q_2UplMKX60bRA')
# print('query: https://open.spotify.com/track/77rj41HJ2iSYuJYdcsucFq?si=-NqSPaB8Q_2UplMKX60bRA')
# print('-----------------------------------------------------------------------------')
# print(w.getSongName())
# print(w.getYoutubeLink())
# print()
# 
# w1 = q.searchAllFromUrl('https://open.spotify.com/track/4Tm7vJMSIcb8FcrLsLnirt?si=z1ouDBffR6yFI57cDkd5hw')
# print('query: https://open.spotify.com/track/4Tm7vJMSIcb8FcrLsLnirt?si=z1ouDBffR6yFI57cDkd5hw')
# print('-----------------------------------------------------------------------------')
# 
# for w in w1:
#     print(w.getSongName())
#     print(w.getYoutubeLink())
#     print()

while True:
    query = input('\nSearch Query: ')

    if query == 'quit()':
        break

    t1 = datetime.now()
    w = q.searchFromName(query)
    print()
    print(w.getSongName())
    print(w.getContributingArtists())
    print(w.getYoutubeLink())
    t2 = datetime.now()

    print(t2-t1)

#while True:
#    query = input('search query: ')
#5
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