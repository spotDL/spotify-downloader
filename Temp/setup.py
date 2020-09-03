from setuptools import setup

setup(
    name = 'spotdl',

    packages = [
        'spotdl',
        'spotdl.dlTools',
        'spotdl.providers',
        'spotdl.utils'
    ],

    version = '3.0.0',
    licence = 'MIT',

    install_requires = [
        'spotipy >= 2.12.0',
        'mutagen >= 1.41.1',
        'tqdm >= 4.45.0',
        'fuzzywuzzy >= 0.17.0',
        'requests >= 2.20.0'
    ],
    python_requires = '>= 3.6',

    entry_points = {
        'console_scripts': [
            'spotdl = spotdl.__main__:main'
        ]
    },

    description = 'Matches and downloads songs/albums/playlists from spotify with ~99% accuracy',

    # can we add multiple authors?
    author = 'Ritiek Malhotra',
    author_email = 'ritiekmalhotra123@gmail.com',

    url = 'https://github.com/ritiek/spotify-downloader',
    download_url = 'https://pypi.org/project/spotdl/',

    keywords = [
        'spotify',
        'downloader',
        'music',
        'youtube',
        'mp3',
        'album',
        'playlist',
        'metadata'
    ],

    classifiers = [
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Multimedia",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ]
)