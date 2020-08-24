'''
Handles the embedding of metadata into audio files, uses ID3 v2.3 tags.
'''



#===============
#=== Imports ===
#===============

# generic imports:
from urllib.request import urlopen
#from spotdl.utils.loggingBase import getSubLoggerFor

# The following help embed metadata:
# Renaming imports to conform to naming conventions 
from mutagen.easyid3 import EasyID3 as easyId3, ID3 as id3

# Renaming imports so that their purpose is clear
from mutagen.id3 import APIC as albumCover, USLT as lyricData

# for downloading audio
from pytube import YouTube
from os import system as runInShell



#====================
#=== Initializing ===
#====================
#logger = getSubLoggerFor('utility')



#=================
#=== Functions ===
#=================

def downloadTrack(link, folder):
    # should be fairly self explanatory...
    youtubeHandler = YouTube(link)
    
    trackStreams = youtubeHandler.streams.get_audio_only()
    savedPath = trackStreams.download(output_path = folder)

    return savedPath

# Used a Pool (16 processes), converted 520 .flac files (~22.8gB)
# in 19.28.02 mins, single proc took 62 mins.

def encodeToMp3(filePath, outFolder = '.\\', overwriteFiles=False):
    # ffmpeg handles the details of conversions, just have to specify the
    # input and output:
    #
    # ffmpeg -i $inputFile.anyExtension $outputFile.mp3

    rIndexOfSlash = filePath.rfind('\\')

    extensionIndex = filePath.rfind('.')
    extension = filePath[extensionIndex + 1 :].lower()

    command = ''

    if overwriteFiles:
        command = 'ffmpeg -v quiet -y -i "%s" "%s.mp3"'
    else:
        command = 'ffmpeg -v quiet -n -i "%s" "%s.mp3"'

    if extension != '.txt' and extension != '.mp3':
        extensionLessFile = filePath[rIndexOfSlash + 1 : extensionIndex]
        formattedCommand = command % (filePath, outFolder + extensionLessFile)
        runInShell(formattedCommand)


# currently supports only mp3
def embedDetails(filePath, metadata):
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
    audioFile['tracknumber'] = metadata.getTrackNumber()

    # geners [TODO]

    # duration
    audioFile['length'] = metadata.getLength()

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
    lyrics = metadata.getLyrics()

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