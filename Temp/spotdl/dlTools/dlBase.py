'''
Handles the embedding of metadata into audio files, uses ID3 v2.3 tags.
'''



#===============
#=== Imports ===
#===============

# generic imports:
from urllib.request import urlopen
from spotdl.utils.loggingBase import getSubLoggerFor

# The following help embed metadata:
# Renaming imports to conform to naming conventions 
from mutagen.easyid3 import EasyID3 as easyId3, ID3 as id3

# Renaming imports so that their purpose is clear
from mutagen.id3 import APIC as albumCover, USLT as lyricData

# for downloading audio
from pytube import YouTube

from os import system as runInShell, makedirs, remove, rename
from os.path import join, exists



#====================
#=== Initializing ===
#====================
logger = getSubLoggerFor('utility')



#=================
#=== Functions ===
#=================

def downloadTrack(link, folder):
    '''
    `str` `link` : link of a song from YouTube

    `str` `folder` : path to folder where track is to be downloaded

    downloads audio from youtube link and returns path of saved file.
    This function doesn't create a destination folder if it doesn't exist
    on the file system
    '''

    # should be fairly self explanatory...
    youtubeHandler = YouTube(link)
    
    trackStreams = youtubeHandler.streams.get_audio_only()
    savedPath = trackStreams.download(output_path = folder)

    return savedPath

# Used a Pool (16 processes), converted 520 .flac files (~22.8gB)
# in 19.28.02 mins, single proc took 62 mins.

def convertToMp3(filePath, outFolder, overwriteFiles = False):
    '''
    `str` `filePath` : path to file to be converted

    `str` `outFolder` : path to output folder

    `bool` `overwriteFiles` : flag indicating weather to overwrite file or not

    converts file at `filePath` to mp3 and outputs the resultant .mp3 file at
    `outFolder`. This function doesn't create the necessary directories. Note
    that no explicit notification is provided as to weather the file is
    overwritten or skipped
    '''

    # ffmpeg handles the details of conversions, just have to specify the
    # input and output:
    #
    # ffmpeg -i $inputFile.anyExtension $outputFile.mp3

    rIndexOfSlash = filePath.rfind('\\')
    extensionIndex = filePath.rfind('.')

    extensionLessFile = filePath[rIndexOfSlash + 1 : extensionIndex]
    outFile = join(outFolder, extensionLessFile)

    if overwriteFiles:
        command = 'ffmpeg -v quiet -y -i "%s" "%s.mp3"'
        formattedCommand = command % (filePath, outFile)
        runInShell(formattedCommand)
    else:
        command = 'ffmpeg -v quiet -n -i "%s" "%s.mp3"'
        formattedCommand = command % (filePath, outFile)
        runInShell(formattedCommand)
    
    return outFile + '.mp3'

# currently supports only mp3
def embedDetails(filePath, songObj):
    '''
    `str` `filePath` : path to file whose metadata is to be embedded

    `metadataObj` `metadata` : object containing metadata of the given song.
    Object should implement the metadata object interface

    Embeds metadata to given file using ID3 v2.3 tags. ID3 v2.4 is not used as
    Windows systems do not support them and hence metadata would not display
    '''

    metadata = songObj.getMetadata()

    # Setting the simple ID3 values
    audioFile = easyId3(filePath)

    # Get rid of existing ID3 v1 & v2 values
    audioFile.delete()

    # A note for the logs...
    # str.rfind returns the index of the character, filePath[stringNameIndex]
    # would return '\\song name.mp3', I don't want the '\\'
    fileNameIndex = filePath.rfind('\\')

    fileName = filePath[fileNameIndex + 1]
    logger.info('Embedding ID3 metadata to %s >' % fileName)

    # song name
    audioFile['title'] = metadata.getSongName()

    #track number
    audioFile['tracknumber'] = str(metadata.getTrackNumber())

    # geners
    genres = metadata.getGenres()

    if genres != None:
        audioFile['genre'] = genres

    # all artists involved in the song
    audioFile['artist'] = metadata.getContributingArtists() # what separator?

    # album name
    audioFile['album'] = metadata.getAlbumName()

    # album artists (all of them)
    audioFile['albumartist'] = metadata.getAlbumArtists()  # What separator?

    # album release date
    audioFile['date'] = metadata.getAlbumRelease()
    audioFile['originaldate'] = metadata.getAlbumRelease()

    # saving metadata using ID3 v2.3 tags, default is v2.4 but windows doesn't
    # yet support ID3 v2.4 tags
    audioFile.save(v2_version = 3)

    # Set the not so simple tags
    audioFile = id3(filePath)

    # Get album art image as bytes from server
    rawAlbumArt = urlopen(metadata.getAlbumArtUrl()).read()

    # Set album art
    audioFile['APIC'] = albumCover(
        encoding = 3,
        mime = 'image/jpeg',
        type = 3,
        desc = 'Cover',
        data = rawAlbumArt
    )

    # Returns 'None' if lyrics not found
    lyrics = songObj.getLyrics()

    # 'None' evaluates to 'False'
    if lyrics:

        # Set lyrics (not synchronized)
        audioFile['USLT'] = lyricData(
            encoding = 3,
            desc = 'Lyrics',
            text = lyrics
        )
    
    # Same as before, save using ID3 v2.3 tags
    audioFile.save(v2_version = 3)

    logger.info('Metadata successfully applied')

def process(songObj, dlTracker = None, folder = '.'):
    '''
    `songObj` `songObj` : An object implementing the song object interface
    representing the song to be downloaded

    `Autoproxy` `dlTracker` : an instance of `downloadTracker` running on a
    separate process to handle download tracking and user-notification. Pass
    only if downloading multiple songs in parallel (i.e. using this function as
    the 'func' parameter for a `multiprocessing.Pool`)

    `str` `folder` : path to folder where songs are to be saved

    downloads the passed song, converts it to MP3, embeds metadata. If
    `dlTracker` is passed, this function also keeps track of download progress
    through a '.spotifyTrackingFile'
    '''
    
    # create a temp folder if not present
    tmpPath = join(folder, 'Temp')

    if not exists(tmpPath):
        makedirs(tmpPath)
    
    if dlTracker:
        dlTracker.notifyDownloadStart()
    
    # build name string that goes $artist-1, ..., $artist-N - $songName.mp3
    songRenameName = ''

    for artist in songObj.getContributingArtists():
        songRenameName += artist + ', '

    songRenameName = songRenameName[:-2] + ' - ' + songObj.getSongName() + '.mp3'
    for dissallowedChar in ['/', '?', '\\', '*','|', '<', '>']:
        if dissallowedChar in songRenameName:
            songRenameName = songRenameName.replace(dissallowedChar, '')

    songRenameName = songRenameName.replace('"', "'").replace(':', ' -')
    renamedPath = join(folder, songRenameName)
    
    if exists(renamedPath) and dlTracker:
        dlTracker.notifySkip(songObj)
    
    else:
        try:
            # if at all there is an error, it'll be during the download stage,
            # the whole thing is put in a try-except clause as if the download
            # screws up, everything else will too
            
            # download song
            downloadedPath = downloadTrack(
                songObj.getYoutubeLink(),
                tmpPath
            )
    
            if dlTracker:
                dlTracker.notifyConversionStart()
    
            # convert to .mp3
            convertedPath = convertToMp3(
                downloadedPath,
                tmpPath
                )
    
            if dlTracker:
                dlTracker.notifyEmbeddingStart()
    
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
    
            # actually rename the file from the renamed path we left hanging earlier
            rename(convertedPath, renamedPath)
    
            # notify download completion to update the corresponding .spotdlTrackingFile
            if dlTracker:
                dlTracker.notifyCompletion(songObj)
    
        except:
            if dlTracker:
                dlTracker.notifyDownloadError()