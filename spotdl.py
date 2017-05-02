#!/usr/bin/env python

from bs4 import BeautifulSoup
from random import choice
from shutil import copyfileobj
from sys import path
import spotipy
import eyed3
import requests
import pafy
import os
import argparse
import spotipy.util as util

eyed3.log.setLevel("ERROR")

os.chdir(path[0])

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

def initializeInput(command):
	if command == 'list':
		grabList(file='list.txt')
	elif command == 'exit':
		graceQuit()
	else:
		grabSingle(raw_song=command, number=None)

def getInputLink(links):
	while True:
		try:
			the_chosen_one = int(raw_input('>> Choose your number: '))
			if the_chosen_one >= 1 and the_chosen_one <= len(links):
				break
			else:
				print('Choose a valid number!')
		except ValueError:
			print('Choose a valid number!')
	return links[the_chosen_one-1]

def isSpotify(raw_song):
	if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1):
		return True
	else:
		return False

def generateSongName(raw_song):
	if isSpotify(raw_song):
		tags = generateMetaTags(raw_song)
		raw_song = (tags['artists'][0]['name'] + ' - ' + tags['name']).encode('utf-8')
	return raw_song

def generateMetaTags(raw_song):
	if isSpotify(raw_song):
		return spotify.track(raw_song)
	else:
		print spotify.search(raw_song, limit=1)
		return spotify.search(raw_song, limit=1)

def generateSearchURL(song):
	URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + song.replace(" ", "%20").encode('utf-8')
	return URL

def generateYouTubeURL(raw_song):
	song = generateSongName(raw_song)
	searchURL = generateSearchURL(song)
	items = requests.get(searchURL).text
	items_parse = BeautifulSoup(items, "html.parser")
	check = 1
	if args.manual:
		links = []
		print(song)
		print('')
		for x in items_parse.find_all('h3', {'class':'yt-lockup-title'}):
			if not x.find('channel') == -1 or not x.find('googleads') == -1:
				print((str(check) + '. ' + x.get_text()).encode('utf-8'))
				links.append(x.find('a')['href'])
				check += 1
		result = getInputLink(links)
	else:
		result = items_parse.find_all(attrs={'class':'yt-uix-tile-link'})[0]['href']
		while not result.find('channel') == -1 or not result.find('googleads') == -1:
			result = items_parse.find_all(attrs={'class':'yt-uix-tile-link'})[check]['href']
			check += 1
	full_link = "youtube.com" + result
	return full_link

def goPafy(raw_song):
	trackURL = generateYouTubeURL(raw_song)
	return pafy.new(trackURL)

def getYouTubeTitle(content, number):
	title = (content.title).encode("utf-8")
	if number == None:
		return title
	else:
		return str(number) + '. ' + title

def generateFileName(content):
	return ((content.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").replace(" ", "_")).encode('utf-8')

def downloadSong(content):
	music_file = generateFileName(content)
	link = content.getbestaudio(preftype="m4a")
	link.download(filepath="Music/" + music_file + ".m4a")

def convertToMP3(music_file):
	if os.name == 'nt':
		os.system('Scripts\\avconv.exe -loglevel 0 -i "' + 'Music/' + music_file + '.m4a" -ab 192k "' + 'Music/' + music_file + '.mp3"')
	else:
		os.system('avconv -loglevel 0 -i "' + 'Music/' + music_file + '.m4a" -ab 192k "' + 'Music/' + music_file + '.mp3"')
	os.remove('Music/' + music_file + '.m4a')

def checkExists(music_file, raw_song, islist):
	if os.path.exists("Music/" + music_file + ".m4a.temp"):
		os.remove("Music/" + music_file + ".m4a.temp")
	if args.no_convert:
		extension = '.m4a'
	else:
		if os.path.exists("Music/" + music_file + ".m4a"):
			os.remove("Music/" + music_file + ".m4a")
		extension = '.mp3'
	if os.path.isfile("Music/" + music_file + extension):
		if extension == '.mp3':
			audiofile = eyed3.load("Music/" + music_file + extension)
			if isSpotify(raw_song) and not audiofile.tag.music_file == (generateMetaTags(raw_song))['name']:
				os.remove("Music/" + music_file + extension)
				return False
		if islist:
			return True
		else:
			prompt = raw_input('Song with same name has already been downloaded. Re-download? (y/n): ').lower()
			if prompt == "y":
				os.remove("Music/" + music_file + extension)
				return False
			else:
				return True

def trimSong(file):
	with open(file, 'r') as fin:
		data = fin.read().splitlines(True)
	with open(file, 'w') as fout:
		fout.writelines(data[1:])

def fixSong(music_file, meta_tags):
	audiofile = eyed3.load("Music/" + music_file + '.mp3')
	audiofile.tag.artist = meta_tags['artists'][0]['name']
	audiofile.tag.album = meta_tags['album']['name']
	audiofile.tag.title = meta_tags['name']
	albumart = (requests.get(meta_tags['album']['images'][0]['url'], stream=True)).raw
	with open('last_albumart.jpg', 'wb') as out_file:
		copyfileobj(albumart, out_file)
	albumart = open("last_albumart.jpg", "rb").read()
	audiofile.tag.images.set(3,albumart,"image/jpeg")
	audiofile.tag.save(version=(2,3,0))

def grabSingle(raw_song, number):
	if number:
		islist = True
	else:
		islist = False
	content = goPafy(raw_song)
	print getYouTubeTitle(content, number)
	music_file = generateFileName(content)
	if not checkExists(music_file, raw_song, islist=islist):
		downloadSong(content)
		print('')
		if not args.no_convert:
			print('Converting ' + music_file + '.m4a to mp3')
			convertToMP3(music_file)
			print('Fixing meta-tags')
			meta_tags = generateMetaTags(raw_song)
			fixSong(music_file, meta_tags)

def grabList(file):
	lines = open(file, 'r').read()
	lines = lines.splitlines()
	try:
		lines.remove('')
	except ValueError:
		pass
	print('Total songs in list = ' + str(len(lines)) + ' songs')
	number = 1
	for raw_song in lines:
		try:
			grabSingle(raw_song, number=number)
			trimSong(file)
			number += 1
			print('')
		except KeyboardInterrupt:
			graceQuit()
		except Exception as e:
			print e
			lines.append(raw_song)
			trimSong(file)
			with open(file, 'a') as myfile:
				myfile.write(raw_song)
			print('Failed to download song. Will retry after other songs.')

def graceQuit():
		print('')
		print('')
		print('Exitting..')
		exit()

while True:
	for m in os.listdir('Music/'):
		if m.endswith('.m4a.temp'):
			os.remove('Music/' + m)
	print('')
	command = raw_input('>> Enter a song/cmd: ').decode('utf-8').encode('utf-8')
	print('')
	initializeInput(command)
