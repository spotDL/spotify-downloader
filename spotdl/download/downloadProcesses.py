from os import makedirs, remove, system as run_in_shell
from os.path import join, exists

from pytube import YouTube

#! These aren't used, they are for typechecking with mypy
from spotdl.search.songObj import SongObj
from typing import Callable

def get_clean_song_name(songObj: SongObj) -> str:
    '''
    '''

    artistNameString = ''

    #! we eliminate contributing artist names that are also in the song name, else we
    #! would end up with things like 'Jetta, Mastubs - I'd love to change the world
    #! (Mastubs REMIX).mp3' which is kinda an odd file name.
    for artist in songObj.get_contributing_artists():
        if artist.lower() not in songObj.get_song_name().lower():
            artistNameString += artist + ', '
    
    #! Now the artistNameString ends with 'name1, ..., nameN, ' - we don't want the last
    #! ', ' so we remove it 
    songNameString = artistNameString[:-2] + ' - ' + songObj.get_song_name()

    #! removing disallowed charaters (Windows, Mac & Linux)
    for forbiddenChar in ['/', '?', '\\', '*','|', '<', '>']:
        if forbiddenChar in songNameString:
            songNameString = songNameString.replace(forbiddenChar, '')
    
    #! double quotes (") and semi-colons (:) are also disallowed characters but we would
    #! like to retain their equivalents, so they aren't removed in the prior loop
    songNameString = songNameString.replace('"', "'").replace(': ', ' - ')

    return songNameString



def download_song(songObj: SongObj, downloadFolder: str,
                                    progressHook: Callable = None) -> str:
    '''
    `songObj` `SongObj`: song to be downloaded
    
    `str` `downloadFolder`: folder to which the song is to be downloaded

    `function` `progressHook`: function passed to pytube to record download
    progress

    RETURNS `str` of the path to downloaded file

    Note that the song though only audio is stored in an `.mp4` container.
    If the `downloadPath` doesn't exist, it is created. the downloaded file will
    be under `downloadedPath\Temp`.
    '''

    songName = get_clean_song_name(songObj)

    tempFolder = join(downloadFolder, 'Temp')
    if not exists(tempFolder):
        makedirs(tempFolder)


    # skip download if downloaded and converted file exists
    convertedFilePath = join(downloadFolder, songName) + '.mp3'
    if exists(convertedFilePath):
        #! convenient exit to the song
        return None
    
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
    convertedFilePath = downloadFilePath.replace('\Temp', '').replace('.mp4', '.mp3')

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
