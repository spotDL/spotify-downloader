from os import makedirs, remove, system as run_in_shell
from os.path import join, exists

from pytube import YouTube

from mutagen.easyid3 import EasyID3, ID3
from mutagen.id3 import USLT
from mutagen.id3 import APIC as AlbumCover

from urllib.request import urlopen

#! These aren't used, they are for typechecking with mypy
from spotdl.search.songObj import SongObj
from typing import Callable


def download_song_to_local(songObj: SongObj, downloadFolder: str,
                                    progressHook: Callable = None) -> str:
    '''
    `songObj` `SongObj`: song to be downloaded
    
    `str` `downloadFolder`: folder to which the song is to be downloaded

    `function` `progressHook`: function passed to pytube to record download
    progress

    RETURNS `str` of the path to downloaded file

    Note that the song though only audio is stored in an `.mp4` container.
    If the `downloadPath` doesn't exist, it is created. the downloaded file will
    be under `downloadedPath\\Temp`.
    '''

    songName = songObj.get_clean_song_name()

    tempFolder = join(downloadFolder, 'Temp')
    if not exists(tempFolder):
        makedirs(tempFolder)


    # skip download if downloaded and converted file exists
    convertedFilePath = join(downloadFolder, songName) + '.mp3'
    if exists(convertedFilePath):
        #! convenient exit to the song
        return '@!EXISTS'
    
    # else download the song
    if progressHook:
        youtubeHandler = YouTube(
            url = songObj.get_youtube_link(),
            on_complete_callback = progressHook
        )
    else:
        youtubeHandler = YouTube(
            url = songObj.get_youtube_link()
        )
    
    songAudioStream = youtubeHandler.streams.get_audio_only()

    #! THe actual download, if there is an error, it'll be here.
    try:
        #! pyTube will save the song in .\Temp\$songName.mp4, it doesn't save as '.mp3'
        downloadedFilePath = songAudioStream.download(
            output_path   = tempFolder,
            filename      = songName,
            skip_existing = False
        )

    except:
        #! This is equivalent to a failed download, we do nothing, the song remains on
        #! downloadTrackers download queue and all is well...
        #!
        #! None is again used as a convenient exit
        remove(join(tempFolder, songName) + '.mp4')
        return None
    
    return downloadedFilePath

def convert_song_to_mp3(downloadFilePath:str) -> str:
    #! downloadedFile will be of the form '$someFolder\Temp\songName.mp4',
    #! the following changes that to '$someFolder\songName.mp3', it '\Temp'
    #! isn't part of the downloadFilePath it's ignored
    convertedFilePath = downloadFilePath.replace(r'\Temp', '').replace('.mp4', '.mp3')

    # convert downloaded file to MP3 with normalization

    #! -af loudnorm=I=-7:LRA applies EBR 128 loudness normalization algorithm with
    #! intergrated loudness target (I) set to -17, using values lower than -15
    #! causes 'pumping' i.e. rhythmic variation in loudness that should not
    #! exist -loud parts exaggerate, soft parts left alone.
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

    command = 'ffmpeg -v quiet -y -i "%s" -acodec libmp3lame -abr true -af "apad=pad_dur=2, loudnorm=I=-17" "%s"'
    formattedCommand = command % (downloadFilePath, convertedFilePath)

    run_in_shell(formattedCommand)

    #! Wait till converted file is actually created
    while True:
        if exists(convertedFilePath):
            break
    
    return convertedFilePath

def embed_metadata(songObj: SongObj, convertedFilePath: str) -> str:
    
        # embed song details
    #! we save tags as both ID3 v2.3 and v2.4

    #! The simple ID3 tags
    audioFile = EasyID3(convertedFilePath)

    #! Get rid of all existing ID3 tags (if any exist)
    audioFile.delete()

    #! song name
    audioFile['title'] = songObj.get_song_name()
    audioFile['titlesort'] = songObj.get_song_name()

    #! track number
    audioFile['tracknumber'] = str(songObj.get_track_number())

    #! genres (pretty pointless if you ask me)
    #! we only apply the first available genre as ID3 v2.3 doesn't support multiple
    #! genres and ~80% of the world PC's run Windows - an OS with no ID3 v2.4 support
    genres = songObj.get_genres()

    if len(genres) > 0:
        audioFile['genre'] = genres[0]
    
    #! all involved artists
    audioFile['artist'] = songObj.get_contributing_artists()

    #! album name
    audioFile['album'] = songObj.get_album_name()

    #! album artist (all of 'em)
    audioFile['albumartist'] = songObj.get_album_artists()

    #! album release date (to what ever precision available)
    audioFile['date']         = songObj.get_album_release()
    audioFile['originaldate'] = songObj.get_album_release()

    #! spotify link: in case you wanna re-download your whole offline library,
    #! you can just read the links from the tags and redownload the songs.
    audioFile['website'] = songObj.get_spotify_link() + '; ' \
        + songObj.get_youtube_link() + ';'

    #! save as both ID3 v2.3 & v2.4 as v2.3 isn't fully features and
    #! windows doesn't support v2.4 until later versions of Win10
    audioFile.save(v2_version = 3)

    #! setting the album art
    audioFile = ID3(convertedFilePath)

    rawAlbumArt = urlopen(songObj.get_album_cover_url()).read()

    audioFile['APIC'] = AlbumCover(
        encoding = 3,
        mime = 'image/jpeg',
        type = 3,
        desc = 'Cover',
        data = rawAlbumArt
    )

    #! adding lyrics
    try:
        lyrics = songObj.get_song_lyrics()
        USLTOutput = USLT(encoding=3, lang=u'eng', desc=u'desc', text=lyrics)
        audioFile["USLT::'eng'"] = USLTOutput
    except:
        pass

    audioFile.save(v2_version = 3)
