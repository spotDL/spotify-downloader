from pytube import YouTube

from os import mkdir, remove
from os.path import join, exists

#! Just here for static typing
from spotdl.search.songObj import SongObj
from spotdl.download.progressHandlers import DisplayManager, DownloadTracker

def __get_formatted_name(songObj: SongObj) -> str:
    # build file name of converted file
    artistStr = ''

    #! we eliminate contributing artist names that are also in the song name, else we
    #! would end up with things like 'Jetta, Mastubs - I'd love to change the world
    #! (Mastubs REMIX).mp3' which is kinda an odd file name.
    for artist in songObj.get_contributing_artists():
        if artist.lower() not in songObj.get_song_name().lower():
            artistStr += artist + ', '
    
    #! the ...[:-2] is to avoid the last ', ' appended to artistStr
    formattedFileName = artistStr[:-2] + ' - ' + songObj.get_song_name()

    #! this is windows specific (disallowed chars)
    for disallowedChar in ['/', '?', '\\', '*','|', '<', '>']:
        if disallowedChar in formattedFileName:
            formattedFileName = formattedFileName.replace(disallowedChar, '')
    
    #! double quotes (") and semi-colons (:) are also disallowed characters but we would
    #! like to retain their equivalents, so they aren't removed in the prior loop
    formattedFileName = formattedFileName.replace('"', "'").replace(': ', ' - ')

    return formattedFileName


def __download_audio_from_youtube(songObj: SongObj, displayManager: DisplayManager = None,
                                                    downloadTracker: DownloadTracker = None) -> str:
    #! we explicitly use the os.path.join function here to ensure download is
    #! platform agnostic
    
    # Create a .\Temp folder if not present
    tempFolder = join('.', 'Temp')
    
    if not exists(tempFolder):
        mkdir(tempFolder)

    # if a song is already downloaded skip it
    convertedFileName = __get_formatted_name(songObj)
    convertedFilePath = join('.', convertedFileName + '.mp3')

    if exists(convertedFilePath):
        if displayManager:
            displayManager.notify_download_skip()
        if downloadTracker:
            downloadTracker.notify_download_completion(songObj)
        
        #! None is the default return value of all functions, we just explicitly define
        #! it here as a continent way to avoid executing the rest of the function.
        return None
    
    # download Audio from YouTube
    if displayManager:
        youtubeHandler = YouTube(
            url                  = songObj.get_youtube_link(),
            on_progress_callback = displayManager.pytube_progress_hook
        )
    else:
        youtubeHandler = YouTube(songObj.get_youtube_link())
    
    trackAudioStream = youtubeHandler.streams.get_audio_only()

    #! The actual download, if there is any error, it'll be here,
    try:
        #! pyTube will save the song in .\Temp\$songName.mp4, it doesn't save as '.mp3'
        downloadedFilePath = trackAudioStream.download(
            output_path   = tempFolder,
            filename      = convertedFileName,
            skip_existing = False
        )

        return downloadedFilePath

    except:
        #! This is equivalent to a failed download, we do nothing, the song remains on
        #! downloadTrackers download queue and all is well...
        #!
        #! None is again used as a convenient exit
        remove(join(tempFolder, convertedFileName) + '.mp4')
        return None