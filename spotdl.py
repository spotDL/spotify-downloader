#!/usr/bin/env python

from bs4 import BeautifulSoup
import spotipy
import eyed3
import requests
import pafy
import shutil
import os
import sys
import argparse
#import spotipy.util as util

os.chdir(sys.path[0])

if not os.path.exists("Music"):
	os.makedirs("Music")
open('list.txt', 'a').close()

spotify = spotipy.Spotify()

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--no-convert", help="skip the conversion process and meta-tags", action="store_true")
parser.add_argument("-m", "--manual", help="choose the song to download manually", action="store_true")
args = parser.parse_args()

if args.no_convert:
        print("-n, --no-convert skip the conversion process and meta-tags")
if args.manual:
	print("-m, --manual     choose the song to download manually")

def searchYT(number):
	items = (requests.request(method='GET', url=URL)).text
	items_parse = BeautifulSoup(items, "html.parser")
	check = 1
	if args.manual:
		links = []
		if isSpotify():
			print((content['artists'][0]['name'] + ' - ' + content['name']).encode('utf-8'))
		print('')
		for x in items_parse.find_all('h3', {'class':'yt-lockup-title'}):
			if not x.find('channel') == -1 or not x.find('googleads') == -1:
				print((str(check) + '. ' + x.get_text()).encode('utf-8'))
				links.append(x.find('a')['href'])
				check += 1
		is_error = True
		print('')
		while is_error:
			try:
				the_chosen_one = int(raw_input('>> Choose your number: '))
				if the_chosen_one >= 1 and the_chosen_one <= len(links):
					is_error = False
				else:
					print('Choose a valid number!')
			except KeyboardInterrupt:
				graceQuit()
			except:
				print('Choose a valid number!')
		print('')
		first_result = links[the_chosen_one-1]
	else:
		first_result = items_parse.find_all(attrs={'class':'yt-uix-tile-link'})[0]['href']
		while not first_result.find('channel') == -1 or not first_result.find('googleads') == -1:
			first_result = items_parse.find_all(attrs={'class':'yt-uix-tile-link'})[check]['href']
			check += 1
	del check
	full_link = "youtube.com" + first_result
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
	global extension
	if args.no_convert:
		extension = '.m4a'
	else:
		if os.path.exists("Music/" + title + ".m4a"):
			os.remove("Music/" + title + ".m4a")
		extension = '.mp3'
	if os.path.isfile("Music/" + title + extension):
		if extension == '.mp3':
			audiofile = eyed3.load("Music/" + title + extension)
			if isSpotify() and not audiofile.tag.title == content['name']:
				os.remove("Music/" + title + extension)
				return False
		if islist:
			trimSong()
			return True
		else:
			prompt = raw_input('Song with same name has already been downloaded. Re-download? (y/n/play): ')
			if prompt == "y":
				os.remove("Music/" + title + extension)
				return False
			elif prompt == "play":
				if not os.name == 'nt':
					os.system('mplayer "' + 'Music/' + title + extension + '"')
				else:
					print('Playing ' + title + extension)
					os.system('start ' + 'Music/' + title + extension)
				return True
			else:
				return True

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
	print('Fixing meta-tags')
	audiofile = eyed3.load("Music/" + title + '.mp3')
	audiofile.tag.artist = content['artists'][0]['name']
	audiofile.tag.album = content['album']['name']
	audiofile.tag.title = content['name']
	albumart = (requests.get(content['album']['images'][0]['url'], stream=True)).raw
	with open('last_albumart.jpg', 'wb') as out_file:
		shutil.copyfileobj(albumart, out_file)
	albumart = open("last_albumart.jpg", "rb").read()
	audiofile.tag.images.set(3,albumart,"image/jpeg")
	audiofile.tag.save(version=(2,3,0))

def playSong():
	if not title == '':
		if not os.name == 'nt':
			os.system('mplayer "' + 'Music/' + title + extension + '"')
		else:
			print('Playing ' + title + '.mp3')
			os.system('start ' + 'Music/' + title + extension)

def convertSong():
	print('Converting ' + title + '.m4a to mp3')
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
			if m.endswith('.m4a.temp'):
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
						searchYT(number=y)
						if not checkExists(islist=True):
							downloadSong()
							print('')
							if not args.no_convert:
								convertSong()
								if isSpotify():
									fixSong()
							trimSong()
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
				searchYT(number=None)
				if not checkExists(islist=False):
					downloadSong()
					print('')
					if not args.no_convert:
						convertSong()
						if isSpotify():
							fixSong()
			except KeyboardInterrupt:
				graceQuit()
	except KeyboardInterrupt:
		graceQuit()
