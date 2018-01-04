#!/usr/bin/env python3

from distutils.core import setup

setup(name='Spotify Downloader',
      description='Download Spotify playlists with albumart and meta-tags',
      author='Ritiek Malhotra',
      author_email='ritiekmalhotra123@gmail.com',
      url='https://github.com/ritiek/spotify-downloader',
      license='MIT',
      packages=['core'],
      scripts=['spotdl.py'],
      install_requires=[
        'pathlib',
        'BeautilfulSoup4',
        'youtube_dl',
        'pafy',
        'spotipy',
        'mutagen',
        'unicode-slugify',
        'titlecase',
        'logzero',
      ]
)
