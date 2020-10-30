from setuptools import setup

long_desc = open('README.md', encoding = 'utf-8').read()

setup(
    # 'spotify-downloader' was already taken (＞﹏＜)
    name = "spotdl",
    
    packages = [
        'spotdl',
        'spotdl.search',
        'spotdl.download',
        'spotdl.patches'
    ],

    #! PyPi doesn't allow repeat names, so it essentially considered a patch
    version = '3.1.4',

    install_requires = [
        'spotipy',
        'a-pytube-fork-for-spotdl-users',
        'tqdm',
        'rapidfuzz',
        'requests',
        'mutagen',
    ],

    description="Downloads Spotify music from Youtube with metadata and album art",
    long_description=long_desc,
    long_description_content_type='text/markdown',
    
    author="Mikhail Zex (Not really my name)",
    author_email="unrealengin71+PyPi@gmail.com",

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
