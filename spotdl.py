#!/bin/python

from bs4 import BeautifulSoup
import spotipy
import eyed3
import requests
import pafy
import shutil
import os
import sys
#import spotipy.util as util

os.chdir(sys.path[0])

if not os.path.exists("Music"):
	os.makedirs("Music")
open('list.txt', 'a').close()

spotify = spotipy.Spotify()

def searchYT(number):
	items = (requests.request(method='GET', url=URL)).text
	zoom1 = items.find('yt-uix-tile-link')
	zoom2 = items.find('yt-uix-tile-link', zoom1+1)
	zoom3 = items.find('yt-uix-tile-link', zoom2+1)
	part = items[zoom1-100: zoom2]
	items_parse = BeautifulSoup(part, "html.parser")
	first_result = items_parse.find(attrs={'class':'yt-uix-tile-link'})['href']
	full_link = "youtube.com" + first_result
	#print(full_link)
	global video
	video = pafy.new(full_link)
	global raw_title
	raw_title = (video.title).encode("utf-8")
	global title
	title = ((video.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").replace(" ", "_")).encode('utf-8')
	if not number == None:
		print(str(number) + '. ' + (video.title).encode("utf-8"))
	else:
		print(video.title).encode("utf-8")

def checkExists(islist):
	if os.path.exists("Music/" + title + ".m4a.temp"):
		os.remove("Music/" + title + ".m4a.temp")
	if os.path.exists("Music/" + title + ".mp3"):
		audiofile = eyed3.load("Music/" + title + '.mp3')
		if isSpotify() and not audiofile.tag.title == content['name']:
			os.remove("Music/" + title + '.mp3')
		elif islist:
			trimSong()
			return True
		else:
			prompt = raw_input('Song with same name has already been downloaded.. re-download? (y/n/play): ')
			if prompt == "y":
				os.remove("Music/" + title + ".mp3")
			elif prompt =="play":
				if not os.name == 'nt':
					os.system('mplayer "' + 'Music/' + title + '.mp3"')
				else:
					print('Playing ' + title + '.mp3')
					os.system('start ' + 'Music/' + title + '.mp3')
				return True
			else:
				return True
	return False

def getLyrics():
	if not title == '':
		if song == '':
			link = 'https://duckduckgo.com/html/?q=' + raw_title.replace(' ', '+') + '+musixmatch'
		else:
			link = 'https://duckduckgo.com/html/?q=' + (content['artists'][0]['name'] + ' - ' + content['name']).replace(' ', '+') + '+musixmatch'
		page = requests.request(method='GET', url=link).text
		soup = BeautifulSoup(page, 'html.parser')
		link = soup.find('a', {'class':'result__url'})['href']
		page = requests.request(method='GET', url=link).text
		soup = BeautifulSoup(page, 'html.parser')
		for x in soup.find_all('p', {'class':'mxm-lyrics__content'}):
			print(x.get_text()).encode('utf-8')
	else:
		print('No log to read from..')

def fixSong():
	print 'Fixing meta-tags..'
        audiofile = eyed3.load("Music/" + title + '.mp3')
        audiofile.tag.artist = content['artists'][0]['name']
        audiofile.tag.album = content['album']['name']
        audiofile.tag.title = content['name']
        albumart = (requests.get(content['album']['images'][0]['url'], stream=True)).raw
        with open('last_albumart.jpg', 'wb') as out_file:
                shutil.copyfileobj(albumart, out_file)
        albumart = open("last_albumart.jpg", "rb").read()
        audiofile.tag.images.set(3,albumart,"image/jpeg")
        audiofile.tag.save()

def playSong():
	if not title == '':
		if not os.name == 'nt':
			os.system('mplayer "' + 'Music/' + title + '.mp3"')
		else:
			print('Playing ' + title + '.mp3')
			os.system('start ' + 'Music/' + title + '.mp3')

def convertSong():
	print('Converting ' + title + '.m4a to mp3..')
	if not os.name == 'nt':
		os.system('avconv -loglevel 0 -i "' + 'Music/' + title + '.m4a" -ab 192k "' + 'Music/' + title + '.mp3"')
	else:
		os.system('Scripts\\avconv.exe -loglevel 0 -i "' + 'Music/' + title + '.m4a" -ab 192k "' + 'Music/' + title + '.mp3"')
	os.remove('Music/' + title + '.m4a')

def downloadSong():
	a = video.getbestaudio(preftype="m4a")
	a.download(filepath="Music/" + title + ".m4a")

def isSpotify():
	if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1):
		return True
	else:
		return False

def trimSong():
	with open('list.txt', 'r') as fin:
		data = fin.read().splitlines(True)
	with open('list.txt', 'w') as fout:
		fout.writelines(data[1:])

def trackPredict():
	global URL
	if isSpotify():
		global content
		content = spotify.track(raw_song)
		song = (content['artists'][0]['name'] + ' - ' + content['name']).replace(" ", "%20").encode('utf-8')
		URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + song
	else:
		song = raw_song.replace(" ", "%20")
		URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + song
		song = ''

def graceQuit():
		print('')
		print('')
		print('Exitting..')
		exit()

title = ''
song = ''

while True:
	x = 0
	y = 0
	try:
		for m in os.listdir('Music/'):
			if m.endswith('.temp') or m.endswith('.m4a'):
				os.remove('Music/' + m)
		print('')
		print('')
		raw_song = raw_input('>> Enter a song/cmd: ').decode('utf-8').encode('utf-8')
		print('')
		if raw_song == 'exit':
			exit()
		elif raw_song == 'play':
			playSong()

		elif raw_song == 'lyrics':
			getLyrics()

		elif raw_song == 'list':
			f = open('list.txt', 'r').read()
			lines = f.splitlines()
			for raw_song in lines:
				if not len(raw_song) == 0:
					x = x + 1
			print('Total songs in list = ' + str(x) + ' songs')
			for raw_song in lines:
				try:
					if not len(raw_song) == 0:
						trackPredict()
						print('')
						y = y + 1
						searchYT(y)
						if not checkExists(True):
							downloadSong()
							trimSong()
							print('')
							convertSong()
							if isSpotify():
								fixSong()
					else:
						trimSong()
				except KeyboardInterrupt:
					graceQuit()
				except:
					lines.append(raw_song)
					trimSong()
					with open('list.txt', 'a') as myfile:
						myfile.write(raw_song)
					print('Failed to download song. Will retry after other songs.')
		else:
			try:
				trackPredict()
				searchYT(None)
				if not checkExists(False):
					downloadSong()
					print('')
					convertSong()
					if isSpotify():
						fixSong()
			except KeyboardInterrupt:
				graceQuit()
	except KeyboardInterrupt:
		graceQuit()
