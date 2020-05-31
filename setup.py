from setuptools import setup
import os

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# __version__ comes into namespace from here
with open(os.path.join("spotdl", "version.py")) as version_file:
    exec(version_file.read())

setup(
    # 'spotify-downloader' was already taken :/
    name="spotdl",
    # Tests are included automatically:
    # https://docs.python.org/3.6/distutils/sourcedist.html#specifying-the-files-to-distribute
    packages=[
        "spotdl",
        "spotdl.command_line",
        "spotdl.lyrics",
        "spotdl.lyrics.providers",
        "spotdl.encode",
        "spotdl.encode.encoders",
        "spotdl.metadata",
        "spotdl.metadata.embedders",
        "spotdl.metadata.providers",
        "spotdl.lyrics",
        "spotdl.lyrics.providers",
        "spotdl.authorize",
        "spotdl.authorize.services",
        "spotdl.helpers",
        "spotdl.patch",
    ],
    version=__version__,
    install_requires=[
        "pathlib >= 1.0.1",
        "youtube_dl >= 2017.9.26",
        "pytube3 >= 9.5.5",
        "spotipy >= 2.12.0",
        "mutagen >= 1.41.1",
        "beautifulsoup4 >= 4.6.3",
        "unicode-slugify >= 0.1.3",
        "coloredlogs >= 14.0",
        "lyricwikia >= 0.1.8",
        "PyYAML >= 3.13",
        "appdirs >= 1.4.3",
        "tqdm >= 4.45.0"
    ],
    description="Download songs from YouTube using Spotify song URLs or playlists with albumart and meta-tags.",
    long_description=long_description,
    long_description_content_type="text/markdown",
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
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Multimedia",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ],
    entry_points={"console_scripts": ["spotdl = spotdl:main"]},
)
