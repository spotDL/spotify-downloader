from setuptools import setup

setup(
    # 'spotify-downloader' was already taken (＞﹏＜)
    name = "spotdl",
    
    packages = [
        'spotdl',
        'spotdl.search',
        'spotdl.download',
        'spotdl.patches'
    ],

    version = '3.1.0',

    install_requires = [
        'spotipy',
        'pytube3',
        'tqdm',
        'rapidfuzz',
        'requests',
        'mutagen',
    ],

    description="Downloads Spotify music from Youtube with metadata and album art",
    
    author="Ritiek Malhotra",
    author_email="ritiekmalhotra123@gmail.com",

    license="MIT",

    python_requires=">=3.6",

    url="https://github.com/ritiek/spotify-downloader",
    download_url="https://pypi.org/project/spotdl/",

    keywords=[
        "spotify",
        "downloader",
        "download",
        "music",
        "youtube",
        "mp3",
        "album",
        "metadata",
    ],

    classifiers=[
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
    ],

    entry_points = {
        "console_scripts": ["spotdl = spotdl.__main__:console_entry_point"]
    }
)
