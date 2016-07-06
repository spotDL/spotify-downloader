import mechanize
from bs4 import BeautifulSoup as soup
import pafy
import os

if not os.path.exists("Music"):
	os.makedirs("Music")
print ''
os.system('C:\Python27\Scripts\pip.exe install youtube-dl --upgrade')

def Main():
	script_dir = os.getcwd()
	Title = ''
	while True:
		try:
			print('')
			print('')
			raw_song = raw_input('Enter song to download: ')
			if raw_song == "gg":
				exit()
			elif raw_song == "play":
				if not Title == '':
					print 'Playing: ' + Title
					os.system('"' + script_dir + "\Music\\" + Title + ".m4a" + '"')
				else:
					print 'No log to read from..'
			elif raw_song == "dir":
				print "Opening directory: " + script_dir + "\Music\\"
				os.system("explorer.exe " + script_dir + "\Music")
			elif raw_song == "spotify":
				print ''
				f = open('Music/spotify.txt')
				lines = f.readlines()
				print 'Total songs in spotify.txt = ' + str(len(lines)) + ' songs'
				y = 1
				for x in lines:
					print ''
					song = x.replace(" ", "%20")
					br = mechanize.Browser()
					br.set_handle_robots(False)
					br.addheaders = [("User-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13")]
					URL = "https://www.youtube.com/results?search_query=" + song
					items = br.open(URL).read()

					items_parse = soup(items, "html.parser")
					br.close()
					first_result = items_parse.find(attrs={'class':'yt-uix-tile-link'})['href']

					full_link = "youtube.com" + first_result
					#print full_link

					video = pafy.new(full_link)
					Unencoded_Title = ((video.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_"))
					Title = Unencoded_Title.encode("utf-8")
					print str(y) + '. ' + Title
					y = y + 1
					if os.path.exists("Music/" + Unencoded_Title + ".m4a.temp"):
						os.remove("Music/" + Unencoded_Title + ".m4a.temp")
					if os.path.exists("Music/" + Unencoded_Title + ".m4a"):
						with open('Music/spotify.txt', 'r') as fin:
							data = fin.read().splitlines(True)
						with open('Music/spotify.txt', 'w') as fout:
							fout.writelines(data[1:])
					else:
						audiostreams = video.audiostreams
						for a in audiostreams:
							if a.bitrate == "128k" and a.extension == "m4a":
								a.download(filepath="Music/")
								with open('Music/spotify.txt', 'r') as fin:
									data = fin.read().splitlines(True)
								with open('Music/spotify.txt', 'w') as fout:
									fout.writelines(data[1:])
								print ''

			else:
				song = raw_song.replace(" ", "%20")

				br = mechanize.Browser()
				br.set_handle_robots(False)
				br.addheaders = [("User-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13")]
				URL = "https://www.youtube.com/results?search_query=" + song
				items = br.open(URL).read()

				items_parse = soup(items, "html.parser")
				br.close()
				first_result = items_parse.find(attrs={'class':'yt-uix-tile-link'})['href']

				full_link = "youtube.com" + first_result
				#print full_link

				video = pafy.new(full_link)
				Unencoded_Title = ((video.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_"))
				Title = Unencoded_Title.encode("utf-8")
				print Title
				if os.path.exists("Music/" + Unencoded_Title + ".m4a.temp"):
					os.remove("Music/" + Unencoded_Title + ".m4a.temp")
				if os.path.exists("Music/" + Unencoded__Title + ".m4a"):
					prompt = raw_input('Song with same name has already been downloaded.. re-download? (y/n/play): ')
					if prompt == "y":
						os.remove("Music/" + Unencoded_Title + ".m4a")
						audiostreams = video.audiostreams
						for a in audiostreams:
							if a.bitrate == "128k" and a.extension == "m4a":
								a.download(filepath="Music/")
					elif prompt =="play":
						print 'Playing: ' + Title
						os.system('"' + script_dir + "\Music\\" + Unencoded_Title + ".m4a" + '"')
					else:
						pass
				else:
					audiostreams = video.audiostreams
					for a in audiostreams:
						if a.bitrate == "128k" and a.extension == "m4a":
							a.download(filepath="Music/")
		except KeyboardInterrupt:
			pass

Main()