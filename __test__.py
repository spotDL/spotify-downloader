#! Basic necessities to get the CLI running
from spotdl.search.spotifyClient import initialize
from sys import argv as cliArgs

#! Song Search from different start points
from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj

#! The actual download stuff
from spotdl.download.downloader import DownloadManager

#! to avoid packaging errors
from multiprocessing import freeze_support



if __name__ == '__main__':
	freeze_support()

	initialize(
		clientId='4fe3fecfe5334023a1472516cc99d805',
		clientSecret='0f02b7c483c04257984695007a4a8d5c'
		)
	
	downloader = DownloadManager()


	try:
		song = search_for_song('Rednecker')
		print('song', song.get_song_name(), song.get_album_name())
	except:            
		print('No song named Rednecker could be found on spotify')
	
	try:
		downloader.download_single_song(song)
	except:            
		print('No song named Rednecker could be downloaded')
	
	downloader.close()
