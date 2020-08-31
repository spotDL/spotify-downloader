from os import makedirs, remove, rename
from os.path import join, exists

from spotdl.dlTools.dlBase import *

# initially download to temp folder
# convert, move to top, how to shellIt?

# ALL SHELL COMMANDS ACCEPT WILDCARDS, AND DON'T ASK FOR CONFIRMATION
# COPY   SHELL    -> COPY /Y $srcDir\*.$extension $destDir
# MOVE   SHELL    -> MOVE /Y $srcDir\*.$extension $destDir
# DELETE SHELL    -> DEL  /Q $Dir

# save to .\Temp > convert > embed > mode to topDir > remove from list

def process(songObj, folder = '.'):
    # create a temp folder if not present
    tmpPath = join(folder, 'Temp')

    if not exists(tmpPath):
        makedirs(tmpPath)

    # download song
    downloadedPath = downloadTrack(
        songObj.getYoutubeLink(),
        tmpPath
    )

    # convert to .mp3
    convertedPath = convertToMp3(
        downloadedPath,
        tmpPath
        )
    
    # if the downloaded file is .mp3, it isn't converted or is
    # overwritten by the converted .mp3 file, so we wouldn't want
    # to remove it if the paths are the same
    if convertedPath != downloadedPath:
        remove(downloadedPath)

    # embed metadata
    embedDetails(
        convertedPath,
        songObj
    )