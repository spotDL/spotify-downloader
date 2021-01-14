from spotdl.search import spotifyClient
from spotdl.search import songObj

spotifyClient.initialize(
    clientId='4fe3fecfe5334023a1472516cc99d805',
    clientSecret='0f02b7c483c04257984695007a4a8d5c'
    )

#songLnk = 'https://open.spotify.com/track/22ZRskHarzRNN3yLYlcXEp'

playlist_URI = 'https://open.spotify.com/playlist/37i9dQZF1EpiXbCbU404ST?si=gDiY-y6YTX-RBQ2c1vhvDQ'


import spotdl.aDownload.baseTests as adl
from spotdl.search.songObj import SongObj
from spotdl.search.utils import get_playlist_tracks

import asyncio


async def main():
    q = get_playlist_tracks(playlist_URI)[:8]

    n = int(len(q)/4)
    chunkedq = [q[i:i+n] for i in range(0, len(q), n)]
    cq = asyncio.Queue()
    mq = asyncio.Queue()

    downloaders = [asyncio.create_task(adl.download_and_queue(chunk, cq)) for chunk in chunkedq]
    converters = [asyncio.create_task(adl.convert_and_queue(cq, mq)) for _ in range(4)]
    embedders = [asyncio.create_task(adl.metadata_from_queue(mq)) for _ in range(4)]

    asyncio.gather(*downloaders)
    asyncio.gather(*converters)
    asyncio.gather(*embedders)

asyncio.run(main())







# from spotdl.search.utils import get_playlist_tracks
# from spotdl.download.downloader import DownloadManager
# from spotdl.download.playlist import M3U8

# m3u8 = M3U8()

# w = DownloadManager()
# w.download_multiple_songs(q, m3u8)

# t = m3u8.build_m3u8()
# print(t)

# open(r'.\Temp\OnRepeat.m3u8', 'w').write(t)