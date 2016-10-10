#!/usr/bin/python

import sys
import os

if sys.version_info > (3,0):
        sys.exit("spotdl requires python 2.")

from setuptools import setup, find_packages

if not os.path.exists("Music"):
        os.makedirs("Music")
if not os.name == 'nt':
	os.system('sudo chmod 777 Music')
open('Music/list.txt', 'a').close()
if not os.name == 'nt':
	os.system('sudo chmod 777 Music/list.txt')

setup(name='spotdl',
	version='0.1',
	description='Downloads Songs and Spotify playlists (even for free accounts)',
	author='Ritiek Malhotra',
	author_email='ritiekmalhotra123@gmail.com',
	scripts=['bin/spotdl'],
	url='https://www.github.com/Ritiek/Spotify-Downloader/',
	download_url = 'https://github.com/Ritiek/Spotify-Downloader/tarball/0.1',
	keywords = ['download', 'songs', 'spotify', 'playlists', 'music'],
	classifiers = [],
	)

if os.name == 'nt':
	os.system('copy bin\spotdl Scripts\spotdl.py')
	print ''
	print 'To run the script use: `python.exe Scripts/spotdl.py` in your root python installation folder'
