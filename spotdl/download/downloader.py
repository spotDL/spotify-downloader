from os import remove

from spotdl.download.progressHandlers import    ProgressRootProcess
from spotdl.download.downloadProcesses import   download_song_to_local, \
                                                convert_song_to_mp3, \
                                                embed_metadata

#! These are just for mypy type checking
from spotdl.download.progressHandlers import DisplayManager, DownloadTracker
from spotdl.search.songObj import SongObj

def download_song(songObj: SongObj, displayManager: DisplayManager = None,
                                    downloadTracker: DownloadTracker = None) -> None:
    
    # download the song
    if displayManager:
        progHook = displayManager.pytube_progress_hook
    else:
        progHook = None

    downloadedPath = download_song_to_local(
        songObj = songObj,
        downloadFolder = '.\\',
        progressHook = progHook
    )

    if downloadedPath == '@!EXISTS':
        if displayManager: displayManager.notify_download_skip()
        if downloadTracker: downloadTracker.notify_download_completion(songObj)

        return None

    # convert song
    convertedPath = convert_song_to_mp3(downloadedPath)

    if displayManager:
        displayManager.notify_conversion_completion()
    
    # clear old files
    remove(downloadedPath)

    # embed metadata
    embed_metadata(songObj, convertedPath)


    if displayManager:
        displayManager.notify_conversion_completion()
    
    if downloadTracker:
        downloadTracker.notify_download_completion()