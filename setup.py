import re
import ast
from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()


# This does not work as the dependencies imported are most
# likely just about to be installed :/
# from spotdl import __version__

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('spotdl.py', 'r') as f:
    version = str(ast.literal_eval(_version_re.search(f.read()).group(1)))

setup(
    # 'spotify-downloader' was already taken :/
    name='spotdl',
    py_modules=['spotdl'],
    # Tests are included automatically:
    # https://docs.python.org/3.6/distutils/sourcedist.html#specifying-the-files-to-distribute
    packages=['core'],
    version=version,
    install_requires=[
        'pathlib >= 1.0.1',
        'youtube_dl >= 2017.5.1',
        'pafy >= 0.5.3.1',
        'spotipy >= 2.4.4',
        'mutagen >= 1.37',
        'beautifulsoup4 >= 4.6.0',
        'unicode-slugify >= 0.1.3',
        'titlecase >= 0.10.0',
        'logzero >= 1.3.1',
        'lyricwikia >= 0.1.8',
        'PyYAML >= 3.12'
    ],
    description='Download songs from YouTube using Spotify song URLs or playlists with albumart and meta-tags.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Ritiek Malhotra and the spotify-downloader contributors',
    author_email='ritiekmalhotra123@gmail.com',
    license='MIT',
    url='https://github.com/ritiek/spotify-downloader',
    download_url='https://pypi.org/project/spotify-downloader/',
    keywords=['spotify', 'downloader', 'download', 'music', 'youtube', 'mp3', 'album', 'metadata'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Utilities'
    ],
    entry_points={
        'console_scripts': [
            'spotdl = spotdl:main',
        ],
    }
)
