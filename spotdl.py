#!/bin/python

import mechanize
from bs4 import BeautifulSoup
import pafy
import os
import sys
import spotipy
import eyed3
#import spotipy.util as util

#print sys.path[0]
if not os.name == 'nt':
	script_dir = sys.path[0] + '/'
else:
	script_dir = sys.path[0] + '\\'

os.chdir(script_dir)

if not os.path.exists("Music"):
	os.makedirs("Music")
open('Music/list.txt', 'a').close()

spotify = spotipy.Spotify()

print ''

def Main():
	Title = ''
	label = ''
	while True:
		try:
			for m in os.listdir('Music/'):
				if m.endswith(".temp") or m.endswith(".m4a"):
					os.remove('Music/' + m)
			print('')
			print('')
			raw_song = raw_input('>> Enter a song/cmd: ').encode(utf-8)
			print ''
			if raw_song == "exit":
				exit()
			elif raw_song == "play":
				if not Title == '':
					if not os.name == 'nt':
						os.system('mplayer "' + script_dir + 'Music/' + Title + '.mp3"')
					else:
						print 'Playing..'
						os.system('start ' + script_dir + 'Music\\' + Title + '.mp3')

			elif raw_song == "lyrics":
				br = mechanize.Browser()
				br.set_handle_robots(False)
				br.addheaders = [("User-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13")]
				if not Title == '':
					if label == '':
						link = 'https://duckduckgo.com/html/?q=' + Title.replace(' ', '+') + '+musixmatch'
					else:
						link = 'https://duckduckgo.com/html/?q=' + label.replace(' ', '+') + '+musixmatch'
					page = br.open(link)
					page = page.read()
					soup = BeautifulSoup(page, 'html.parser')
					link = soup.find('a', {'class':'result__url'})['href']
					page = br.open(link).read()
					soup = BeautifulSoup(page, 'html.parser')
					for x in soup.find_all('p', {'class':'mxm-lyrics__content'}):
						print x.get_text()
				else:
					print 'No log to read from..'
				br.close()

			elif raw_song == "list":
					f = open('Music/list.txt')
					lines = f.readlines()
					f.close()
					x = 0
					y = 0
					for songie in lines:
						if not songie == '\n' or not songie == '':
							x = x + 1
					print 'Total songs in list = ' + str(x) + ' songs'
					for songie in lines:
						try:
							if not songie == '\n' or not songie == '':
								if (len(songie) == 22 and songie.replace(" ", "%20") == songie) or (songie.find('spotify') > -1):
									song = songie.replace(songie[-1:], "")
									content = spotify.track(song)
									label = (content['artists'][0]['name'] + ' - ' + content['name']).replace(" ", "%20").encode('utf-8')
									URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + label
								else:
									song = songie.replace(" ", "%20")
									URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + song
									song = ''

								print ''
								br = mechanize.Browser()
								br.set_handle_robots(False)
								br.addheaders = [("User-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13")]
								#print URL
								items = br.open(URL)
								#print items
								items = items.read()
								#print items
								zoom1 = items.find('yt-uix-tile-link')
								zoom2 = items.find('yt-uix-tile-link', zoom1+1)
								zoom3 = items.find('yt-uix-tile-link', zoom2+1)
								part = items[zoom1-100: zoom2]
								items_parse = BeautifulSoup(part, "html.parser")

								#items_parse = soup(items, "html.parser")
								first_result = items_parse.find(attrs={'class':'yt-uix-tile-link'})['href']

								full_link = "youtube.com" + first_result
								#print full_link

								video = pafy.new(full_link)
								Title = ((video.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").replace(" ", "_")).encode('utf-8')
								y = y + 1
								print str(y) + '. ' + ((video.title).encode("utf-8"))
								if os.path.exists("Music/" + Title + ".m4a.temp"):
									os.remove("Music/" + Title + ".m4a.temp")
								download = 1
								if os.path.exists("Music/" + Title + ".mp3"):
									audiofile = eyed3.load("Music/" + Title + '.mp3')
									if ((len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1)) and not audiofile.tag.title == content['name']:
										os.remove("Music/" + Title + '.mp3')
									else:
										with open('Music/list.txt', 'r') as fin:
											data = fin.read().splitlines(True)
										with open('Music/list.txt', 'w') as fout:
											fout.writelines(data[1:])
										download = 0
								if download == 1:
									a = video.getbestaudio(preftype='m4a')
									a.download(filepath="Music/" + Title + ".m4a")
									with open('Music/list.txt', 'r') as fin:
										data = fin.read().splitlines(True)
									with open('Music/list.txt', 'w') as fout:
										fout.writelines(data[1:])
										print ''
									print 'Converting ' + Title + '.m4a' + ' to mp3..'
									if not os.name == 'nt':
										os.system('sudo avconv -loglevel 0 -i "' + script_dir + 'Music/' + Title + '.m4a" -ab 192k "' + script_dir + 'Music/' + Title + '.mp3"')
									else:
										os.system('Scripts\\avconv.exe -loglevel 0 -i "' + script_dir + 'Music/' + Title + '.m4a" -ab 192k "' + script_dir + 'Music/' + Title + '.mp3"')
									os.remove('Music/' + Title + '.m4a')
									if (len(songie) == 22 and songie.replace(" ", "%20") == songie) or (songie.find('spotify') > -1):
										print 'Fixing meta-tags..'
										audiofile = eyed3.load("Music/" + Title + '.mp3')
										audiofile.tag.artist = content['artists'][0]['name']
										audiofile.tag.album = content['album']['name']
										audiofile.tag.title = content['name']
										br.retrieve(content['album']['images'][0]['url'], 'Music/last_albumart.jpg')
										bla = open("Music/last_albumart.jpg","rb").read()
										audiofile.tag.images.set(3,bla,"image/jpeg")
										audiofile.tag.save()
							else:
								with open('Music/list.txt', 'r') as fin:
									data = fin.read().splitlines(True)
								with open('Music/list.txt', 'w') as fout:
									fout.writelines(data[1:])
						except KeyboardInterrupt:
							Main()
						except:
							lines.append(songie)
							with open('Music/list.txt', 'r') as fin:
								data = fin.read().splitlines(True)
							with open('Music/list.txt', 'w') as fout:
								fout.writelines(data[1:])
							with open("Music/list.txt", "a") as myfile:
								myfile.write(songie)
							print 'Could not complete a Song download, will try later..'
						br.close()

			else:
				song = raw_song.replace(" ", "%20")
				br = mechanize.Browser()
				br.set_handle_robots(False)
				br.addheaders = [("User-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13")]
				if (len(raw_song) == 22 and raw_song == song) or (raw_song.find('spotify') > -1):
					content = spotify.track(song)
					label = (content['artists'][0]['name'] + ' - ' + content['name']).replace(" ", "%20").encode('utf-8')
					URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + label
				else:
					URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + song
				items = br.open(URL)
				items = items.read()

				zoom1 = items.find('yt-uix-tile-link')
				zoom2 = items.find('yt-uix-tile-link', zoom1+1)
				zoom3 = items.find('yt-uix-tile-link', zoom2+1)
				part = items[zoom1-100: zoom2]
				items_parse = BeautifulSoup(part, "html.parser")

				#items_parse = soup(items, "html.parser")
				first_result = items_parse.find(attrs={'class':'yt-uix-tile-link'})['href']

				full_link = "youtube.com" + first_result
				#print full_link

				video = pafy.new(full_link)
				Title = ((video.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").replace(" ", "_")).encode('utf-8')
				print ((video.title).encode("utf-8"))
				if os.path.exists("Music/" + Title + ".m4a.temp"):
					os.remove("Music/" + Title + ".m4a.temp")

				download = 1

				if os.path.exists("Music/" + Title + ".mp3"):
					audiofile = eyed3.load("Music/" + Title + '.mp3')
					if ((len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1)) and not audiofile.tag.title == content['name']:
						os.remove("Music/" + Title + '.mp3')
					else:
						prompt = raw_input('Song with same name has already been downloaded.. re-download? (y/n/play): ')
						if prompt == "y":
							os.remove("Music/" + Title + ".mp3")
							download = 1
						elif prompt =="play":
							if not os.name == 'nt':
								os.system('mplayer "' + script_dir + 'Music/' + Title + '.mp3"')
							else:
								print 'Playing..'
								os.system('start ' + script_dir + 'Music\\' + Title + '.mp3')
							download = 0
						else:
							download = 0
				if download == 1:
					a = video.getbestaudio(preftype="m4a")
					a.download(filepath="Music/" + Title + ".m4a")
					print ''
					print 'Converting ' + Title + '.m4a' + ' to mp3..'
					if not os.name == 'nt':
						os.system('sudo avconv -loglevel 0 -i "' + script_dir + 'Music/' + Title + '.m4a" -ab 192k "' + script_dir + 'Music/' + Title + '.mp3"')
					else:
						os.system('Scripts\\avconv.exe -loglevel 0 -i "' + script_dir + 'Music/' + Title + '.m4a" -ab 192k "' + script_dir + 'Music/' + Title + '.mp3"')
					os.remove('Music/' + Title + '.m4a')
					if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1):
						print 'Fixing meta-tags..'
						audiofile = eyed3.load("Music/" + Title + '.mp3')
						audiofile.tag.artist = content['artists'][0]['name']
						audiofile.tag.album = content['album']['name']
						audiofile.tag.title = content['name']
						br.retrieve(content['album']['images'][0]['url'], 'Music/last_albumart.jpg')
						bla = open("Music/last_albumart.jpg","rb").read()
						audiofile.tag.images.set(3,bla,"image/jpeg")
						audiofile.tag.save()
						br.close()
		except KeyboardInterrupt:
			pass

Main()
