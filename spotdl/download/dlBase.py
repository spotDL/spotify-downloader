from spotdl.search.songObj import songObj
from urllib.request import urlopen

from tqdm import tqdm
from os import walk, remove, mkdir, system as runInShell
from os.path import join, exists

from multiprocessing import Pool
import multiprocessing.managers

from mutagen.easyid3 import EasyID3 as easyId3, ID3 as id3
from mutagen.id3 import APIC as albumCover, USLT as lyricData

from pytube import YouTube

from typing import List

class tqdmAltRate(tqdm):

    @property
    def format_dict(self):
        formatDict = super(tqdmAltRate, self).format_dict

        if formatDict['rate']:
            newRate = '{:.2f}'.format( (100/formatDict['rate']) / 60)
        else:
            newRate = '~'

        formatDict.update(rate_min = (newRate + 'min/' + formatDict['unit']))

        return formatDict
    
    def set_progress_to(self, value):
        self.n = value
        self.update(0)

class downloadTracker():
    def __init__(self):
        self.songObjList = []

        self.count = {
            'downloading': 0,
            'converting' : 0,
            'embedding'  : 0
        }

        self.saveFile = None

        self.progressBar = tqdmAltRate(
            total           = 100,
            dynamic_ncols   = True,
            bar_format      = '{desc} {percentage:3.0f}%|{bar}|ETA: {remaining}, {rate_min}',
            unit            = 'song'
        )

    def load_tracking_file(self, trackingFile: str) -> None:
        try:
            file = open(trackingFile, 'r')
            songDataDumps = eval(file.read())
            file.close()
        except FileNotFoundError:
            raise Exception('no such tracking file found: %s' % trackingFile)
            
        self.saveFile = trackingFile

        for dump in songDataDumps:
            self.songObjList.append( songObj.from_dump(dump) )
        
        self.progressBar.total = len(self.songObjList) * 100
    
    def load_song_list(self, songObjList: List[songObj]) -> None:
        self.songObjList = songObjList

        self.backup_to_disk()
        self.progressBar.total = len(self.songObjList) * 100
    
    def backup_to_disk(self) -> None:
        songDataDumps = []

        for song in self.songObjList:
            songDataDumps.append(song.get_data_dump())
        
        if not self.saveFile:
            self.saveFile = self.songObjList[0].get_song_name() + '.spotdlTrackingFile'

        file = open(self.saveFile, 'wb')
        file.write(str(songDataDumps).encode())
        file.close()
    
    def get_song_list(self) -> List[songObj]:
        return self.songObjList
    
    def notify_download_start(self) -> None:
        self.count['downloading'] += 1
    
    def notify_download_fail(self) -> None:
        self.count['downloading'] -= 1
    
    def notify_converting_start(self) -> None:
        self.count['downloading'] -= 1
        self.count['converting']  += 1
    
    def notify_embedding_start(self) -> None:
        self.count['converting'] -= 1
        self.count['embedding']  += 1

        self.progressBar.update(10)
    
    def notify_download_complete(self, song: songObj) -> None:
        self.count['embedding'] -= 1

        self.songObjList.remove(song)
        self.backup_to_disk()

        self.progressBar.update(10)
    
    def notify_download_skip(self, song: songObj) -> None:
        self.count['downloading'] -= 1

        self.songObjList.remove(song)
        self.backup_to_disk()
    
    def notify_download_progress(self, stream, chunk, bytes_remaining) -> None:
        size = stream.filesize

        progressRatio = round(((size - bytes_remaining) / size), ndigits = 2)
        progressAdjusted = (progressRatio * 80) / 30

        self.progressBar.set_progress_to(progressAdjusted)    
    
    def close(self) -> None:
        self.progressBar.close()
    
    def reset(self) -> None:
        self.songObjList = []

        self.saveFile = None

        self.count['downloading'] = 0
        self.count['converting']  = 0
        self.count['embedding']   = 0

        self.progressBar.reset()

# Backup original AutoProxy function
backup_autoproxy = multiprocessing.managers.AutoProxy

def redefined_autoproxy(token, serializer, manager=None, authkey=None,
          exposed=None, incref=True, manager_owned=True):
    # Calling original AutoProxy without the unwanted key argument
    return backup_autoproxy(token, serializer, manager, authkey,
                     exposed, incref)

# Updating AutoProxy definition in multiprocessing.managers package
multiprocessing.managers.AutoProxy = redefined_autoproxy

class downloadTrackerManager(multiprocessing.managers.BaseManager): pass
downloadTrackerManager.register('downloadTracker', downloadTracker)

class downloadManager():
    poolSize = 2

    def __init__(self):
        trackerManager = downloadTrackerManager()
        trackerManager.start()

        self.rootProcess = trackerManager
        self.downloadTracker = trackerManager.downloadTracker()

        self.workerPool = Pool(downloadManager.poolSize)
    
    def download_single(self, song: songObj) -> None:
        self.downloadTracker.reset()

        self.downloadTracker.load_song_list([songObj])

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (self.downloadTracker, songObj)
                    for songObj in self.downloadTracker.get_song_list()
            )
        )
    
    def download_multiple(self, songList: List[songObj]) -> None:
        self.downloadTracker.reset()
        
        self.downloadTracker.load_song_list(songList)

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (self.downloadTracker, songObj)
                    for songObj in self.downloadTracker.get_song_list()
            )
        )
    
    def resume_download_from_tracking_file(self, trackingFilePath: str) -> None:
        self.downloadTracker.reset()
        
        self.downloadTracker.load_tracking_file(trackingFilePath)

        self.workerPool.starmap(
            func     = download_song,
            iterable = (
                (self.downloadTracker, songObj)
                    for songObj in self.downloadTracker.get_song_list()
            )
        )
    
    def close(self) -> None:
        self.downloadTracker.close()
        self.rootProcess.shutdown()

        self.workerPool.close()
        self.workerPool.join()

def download_song(displayManager: downloadTracker, songObj: songObj):

    # create a temp folder if not present
    if not exists('.\\Temp'):
        mkdir('.\\Temp')
    
    
    # build name string that goes $artist-1, ..., $artist-N - $songName.mp3
    songRenameName = ''

    for artist in songObj.get_contributing_artists():
        if artist.lower() not in songObj.get_song_name().lower():
            songRenameName += artist + ', '

    songRenameName = songRenameName[:-2] + ' - ' + songObj.get_song_name() + '.mp3'
    
    for dissallowedChar in ['/', '?', '\\', '*','|', '<', '>']:
        if dissallowedChar in songRenameName:
            songRenameName = songRenameName.replace(dissallowedChar, '')

    songRenameName = songRenameName.replace('"', "'").replace(':', ' -')
    
    renamedPath = join('.', songRenameName)
    
    # if the song is already downloaded, skip it
    if exists(renamedPath):
        displayManager.notify_download_skip(songObj)

        return None
    
    # download audio from youtube
    displayManager.notify_download_start()
    
    youtubeHandler = YouTube(
        songObj.get_youtube_link(),
        on_progress_callback = displayManager.notify_download_progress
    )

    trackStreams = youtubeHandler.streams.get_audio_only()

    try:
        savedPath = trackStreams.download('.\\Temp')
    except:
        displayManager.notify_download_fail()
        return None
    
    # convert to mp3 with audio normalization
    command = 'ffmpeg -v quiet -y -i "%s" -ar 44100 -af loudnorm=i=-7:measured_i=0 -vsync 2 "%s"'
    formattedCommand = command % (savedPath, renamedPath)
    runInShell(formattedCommand)

    # embed details
    #! Setting the simple ID3 values
    audioFile = easyId3(renamedPath)

    # Get rid of existing ID3 v1 & v2 values
    audioFile.delete()

    # song name
    audioFile['title'] = songObj.get_song_name()

    #track number
    audioFile['tracknumber'] = str(songObj.get_track_number())

    # geners
    genres = songObj.get_genres()

    if len(genres) > 0:
        audioFile['genre'] = genres

    # all artists involved in the song
    audioFile['artist'] = songObj.get_contributing_artists()

    # album name
    audioFile['album'] = songObj.get_album_name()

    # album artists (all of them)
    audioFile['albumartist'] = songObj.get_album_artists()

    # album release date
    audioFile['date'] = songObj.get_album_release()
    audioFile['originaldate'] = songObj.get_album_release()

    # saving songObj using ID3 v2.3 tags, default is v2.4 but windows doesn't
    # yet support ID3 v2.4 tags
    audioFile.save(v2_version = 3)
    audioFile.save(v2_version = 4)

    # Set the not so simple tags
    audioFile = id3(renamedPath)

    # Get album art image as bytes from server
    rawAlbumArt = urlopen(songObj.get_album_cover_url()).read()

    # Set album art
    audioFile['APIC'] = albumCover(
        encoding = 3,
        mime = 'image/jpeg',
        type = 3,
        desc = 'Cover',
        data = rawAlbumArt
    )

    # Returns 'None' if lyrics not found
    lyrics = None

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
    audioFile.save(v2_version = 4)