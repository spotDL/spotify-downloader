from spotdl.dlTools.dlBase import embedDetails, downloadTrack

# initially download to temp folder
# convert, move to top, how to shellIt?

# ALL SHELL COMMANDS ACCEPT WILDCARDS, AND DON'T ASK FOR CONFIRMATION
# COPY   SHELL    -> COPY /Y $srcDir\*.$extension $destDir
# MOVE   SHELL    -> MOVE /Y $srcDir\*.$extension $destDir
# DELETE SHELL    -> DEL  /Q $Dir

def process(link, metadata, folder = None):
    # download song
    downloadedPath = downloadTrack(link, folder)

    # embed metadata
    embedDetails(downloadedPath, metadata)