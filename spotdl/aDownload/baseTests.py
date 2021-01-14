import asyncio

import pytube

import os.path as path
import os

#! For typechecking
import typing
from spotdl.search.songObj import SongObj

def get_filesystem_safe_filepath(songObj: SongObj) -> str:
    artistString = ''

    for artist in songObj.get_contributing_artists():
        if artist.lower() not in songObj.get_song_name().lower():
            artistString += f'{artist}, '
    
    convertedFileName = f'{artistString[:-2]} - {songObj.get_song_name()}'

    for character in ['/', '?', '\\', '*', '|', '<', '>', '$']:
        convertedFileName = convertedFileName.replace(character, '')
    
    convertedFileName = convertedFileName.replace('"', "'").replace(':', ' - ')
    convertedFilePath = path.join('.', convertedFileName) + '.mp3'

    return convertedFilePath

async def download_song(songObj: SongObj) -> str:
    # Create a temp folder if one doesn't exist
    tempFolder = path.join('.', 'temp')

    if not path.exists(tempFolder):
        os.mkdir(tempFolder)

    youtubeHandler = pytube.YouTube(songObj.get_youtube_link())
    trackAudioStream = youtubeHandler.streams.filter(only_audio=True).order_by('bitrate').last()

    if not trackAudioStream:
        print(f'''
        Unable to get audio stream for "{songObj.get_song_name()} by {songObj.get_contributing_artists[0]}
        from video: {songObj.get_youtube_link()}
        ''')
    
    else:
        downloadedFilePath = trackAudioStream.download('temp')
        return downloadedFilePath

async def convert_file_to_mp3(downloadedFilePath:str, finalFilePath:str) -> None:
    # convert downloaded file to MP3 with normalization
    
    #! -af loudnorm=I=-7:LRA applies EBR 128 loudness normalization algorithm with
    #! intergrated loudness target (I) set to -17, using values lower than -15
    #! causes 'pumping' i.e. rhythmic variation in loudness that should not
    #! exist -loud parts exaggerate, soft parts left alone.
    #!
    #! dynaudnorm applies dynamic non-linear RMS based normalization, this is what
    #! actually normalized the audio. The loudnorm filter just makes the apparent
    #! loudness constant
    #!
    #! apad=pad_dur=2 adds 2 seconds of silence toward the end of the track, this is
    #! done because the loudnorm filter clips/cuts/deletes the last 1-2 seconds on
    #! occasion especially if the song is EDM-like, so we add a few extra seconds to
    #! combat that.
    #!
    #! -acodec libmp3lame sets the encoded to 'libmp3lame' which is far better
    #! than the default 'mp3_mf', '-abr true' automatically determines and passes the
    #! audio encoding bitrate to the filters and encoder. This ensures that the
    #! sampled length of songs matches the actual length (i.e. a 5 min song won't display
    #! as 47 seconds long in your music player, yeah that was an issue earlier.)
    
    command = f'ffmpeg -v quiet -y -i "{downloadedFilePath}" -acodec libmp3lame -af "apad=pad_dur=2, loudnorm=I=-17" "{finalFilePath}"'

    conversionProcess = await asyncio.subprocess.create_subprocess_shell(command)
    _ = await conversionProcess.communicate()

async def write_id3_tags(songObj:SongObj, filePath:str) -> None:
    asyncio.sleep(5)

async def download_and_queue(songObjList: typing.List[SongObj], converterQueue: asyncio.Queue) -> None:
    for songObj in songObjList:
        downloadedFilePath = await download_song(songObj)
        safeFilePath = get_filesystem_safe_filepath(songObj)

        await converterQueue.put((songObj, downloadedFilePath, safeFilePath))

        print(f'downloaded: {songObj.get_song_name()}')

async def convert_and_queue(converterQueue: asyncio.Queue, metadata_queue:asyncio.Queue) -> None:
    songObj, downloadedFilePath, safeFilePath = await converterQueue.get()
    await convert_file_to_mp3(downloadedFilePath, safeFilePath)

    await metadata_queue.put((songObj, safeFilePath))
    print(f'converted: {songObj.get_song_name()}')

async def metadata_from_queue(metadata_queue: asyncio.Queue) -> None:
    songObj, safeFilePath = await metadata_queue.get()
    await write_id3_tags(songObj, safeFilePath)
    print(f'embedded: {songObj.get_song_name()}')