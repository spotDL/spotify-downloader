#!/usr/bin/python

import sys
import os

if sys.version_info > (3,0):
	sys.exit("YTMusic requires python 2.")

from setuptools import setup, find_packages

setup(name='YT_Music',
      version='0.1',
      description='Downloads Songs and Spotify playlists.',
      author='Ritiek Malhotra',
      author_email='ritiekmalhotra123@gmail.com',
      scripts=['bin/YTMusic'],
      url='https://www.github.com/Ritiek/YTMusic/',
      download_url = 'https://github.com/Ritiek/YTMusic/tarball/0.1',
      keywords = ['download', 'songs', 'spotify', 'playlists', 'music'],
      classifiers = [],
     )
