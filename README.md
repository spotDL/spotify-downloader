# Spotify-Downloader

[![Build Status](https://travis-ci.org/ritiek/spotify-downloader.svg?branch=master)](https://travis-ci.org/ritiek/spotify-downloader)
[![Coverage Status](https://codecov.io/gh/ritiek/spotify-downloader/branch/master/graph/badge.svg)](https://codecov.io/gh/ritiek/spotify-downloader)
[![Docker Build Status](https://img.shields.io/docker/build/ritiek/spotify-downloader.svg)](https://hub.docker.com/r/ritiek/spotify-downloader)

- Downloads songs from YouTube in an MP3 format by using Spotify's HTTP link.

- Can also download a song by entering its artist and song name (in case if you don't have the Spotify's HTTP link for some song).

- Automatically applies metadata to the downloaded song which include:

  - Title
  - Artist
  - Album
  - Album art
  - Lyrics (if found on http://lyrics.wikia.com)
  - Album artist
  - Genre
  - Track number
  - Disc number
  - Release date
  - And more...

- Works straight out of the box and does not require to generate or mess with your API keys.

That's how your music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290"><img src="http://i.imgur.com/5vhk3HY.png" width="290"><img src="http://i.imgur.com/RDTCCST.png" width="290">

## Installation

- **This tool supports only Python 3**, Python 2 compatibility was dropped
because of the way it deals with unicode.
If you need to use Python 2 though, check out the (old) `python2` branch.

- Note: `play` and `lyrics` commands have been deprecated in the current branch
since they were not of much use and created unnecessary clutter.
You can still get them back by using `old` branch though.

### Debian, Ubuntu, Linux & Mac

```
$ cd
$ git clone https://github.com/ritiek/spotify-downloader
$ cd spotify-downloader
$ pip install -U -r requirements.txt
```

**Important:** if you have installed both Python 2 and 3, the `pip` command
could invoke an installation for Python 2. To see which Python version `pip`
refers to, try `$ pip -V`. If it turns out `pip` is your Python 2 pip, try
`$ pip3 install -U -r requirements.txt` instead.

You'll also need to install FFmpeg for conversion
(use `--avconv` if you'd like to use that instead):

Linux: `$ sudo apt-get install ffmpeg`

Mac: `$ brew install ffmpeg --with-libmp3lame --with-libass --with-opus --with-fdk-aac`

If it does not install correctly, you may have to build it from source.
For more info see https://trac.ffmpeg.org/wiki/CompilationGuide.

### Windows

Assuming you have Python 3
([preferably v3.6 or above to stay away from Unicode errors](https://stackoverflow.com/questions/30539882/whats-the-deal-with-python-3-4-unicode-different-languages-and-windows)) already installed and in PATH.

- Download and extract the [zip file](https://github.com/ritiek/spotify-downloader/archive/master.zip)
from master branch.

- Download FFmpeg for Windows from [here](http://ffmpeg.zeranoe.com/builds/).
Copy `ffmpeg.exe` from `ffmpeg-xxx-winxx-static\bin\ffmpeg.exe` to PATH
(usually C:\Windows\System32\) or just place it in the root directory extracted
from the above step.

- Open `cmd` and type `$ pip install -U -r requirements.txt` to install dependencies.
The same note about `pip` as for Debian, Ubuntu, Linux & Mac applies.

## Instructions for Downloading Songs

**Important:** as like with `pip`, there might be no `$ python3` command.
This is most likely the case when you have only Python 3 but not 2 installed.
In this case try the `$ python` command instead of `$ python3`,
but make sure `$ python -V` gives you a `Python 3.x.x`!

- For all available options, run `$ python3 spotdl.py --help`.

```
usage: spotdl.py [-h]
                 (-s SONG | -l LIST | -p PLAYLIST | -b ALBUM | -u USERNAME)
                 [-m] [-nm] [-a] [-f FOLDER] [--overwrite {force,prompt,skip}]
                 [-i INPUT_EXT] [-o OUTPUT_EXT] [-ff] [-dm] [-d] [-mo] [-ns]
                 [-ll {INFO,WARNING,ERROR,DEBUG}]

Download and convert songs from Spotify, Youtube etc.

optional arguments:
  -h, --help            show this help message and exit
  -s SONG, --song SONG  download song by spotify link or name (default: None)
  -l LIST, --list LIST  download songs from a file (default: None)
  -p PLAYLIST, --playlist PLAYLIST
                        load songs from playlist URL into <playlist_name>.txt
                        (default: None)
  -b ALBUM, --album ALBUM
                        load songs from album URL into <album_name>.txt
                        (default: None)
  -u USERNAME, --username USERNAME
                        load songs from user's playlist into
                        <playlist_name>.txt (default: None)
  -m, --manual          choose the song to download manually (default: False)
  -nm, --no-metadata    do not embed metadata in songs (default: False)
  -a, --avconv          Use avconv for conversion otherwise set defaults to
                        ffmpeg (default: False)
  -f FOLDER, --folder FOLDER
                        path to folder where files will be stored in (default:
                        Music)
  --overwrite {force,prompt,skip}
                        change the overwrite policy (default: prompt)
  -i INPUT_EXT, --input-ext INPUT_EXT
                        prefered input format .m4a or .webm (Opus) (default:
                        .m4a)
  -o OUTPUT_EXT, --output-ext OUTPUT_EXT
                        prefered output extension .mp3 or .m4a (AAC) (default:
                        .mp3)
  -ff, --file-format    File format to save the downloaded song with, each tag
                        is surrounded by curly braces. Possible formats:
                        ['track_name', 'artist', 'album', 'album_artist',
                        'genre', 'disc_number', 'duration', 'year',
                        'original_date', 'track_number', 'total_tracks',
                        'isrc'] (default: {artist} - {track_name})
  -dm, --download-only-metadata
                        download songs for which metadata is found (default:
                        False)
  -d, --dry-run         Show only track title and YouTube URL (default: False)
  -mo, --music-videos-only
                        Search only for music on Youtube (default: False)
  -ns, --no-spaces      Replace spaces with underscores in file names
                        (default: False)
  -ll {INFO,WARNING,ERROR,DEBUG}, --log-level {INFO,WARNING,ERROR,DEBUG}
                        set log verbosity (default: INFO)
  -c CONFIG_FILE_PATH --config CONFIG_FILE_PATH
                        Replace with custom config.yml file (default: None)                      
```

#### Download by Name

For example

- We want to download Fade by Alan Walker,
simply run `$ python3 spotdl.py --song "alan walker fade"`.

- The script will automatically look for the best matching song and
download it in the folder `Music/` placed in the root directory of the code base.

- It will now convert the song to an mp3 and try to fix meta-tags
and album-art by looking up on Spotify.

#### Download by Spotify Link (Recommended)

For example

- We want to download the same song (i.e: Fade by Alan Walker) but using
Spotify Link this time that looks like  `https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l`,
you can copy it from your Spotify desktop or mobile app by right clicking
or long tap on the song and copy HTTP link.

- Run `$ python3 spotdl.py --song https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l`,
it should download Fade by Alan Walker.

- Just like before, it will again convert the song to an mp3 but since we used
a Spotify HTTP link, the script is guaranteed to fetch the correct meta-tags and album-art.

#### Download by File

For example

- We want to download `Fade by Alan Walker`, `Sky High by Elektromania`
and `Fire by Elektromania` just using a single command.

Let's suppose, we have the Spotify link for only `Fade by Alan Walker` and
`Fire by Elektromania`.

No problem!

- Just make a `list.txt` in the same folder as the script and add all the
songs you want to download, in our case it is

(if you are on Windows, just edit `list.txt` -
i.e `C:\Python36\spotify-downloader-master\list.txt`)

```
https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l
elektromania sky high
https://open.spotify.com/track/0fbspWuEdaaT9vfmbAZr1C
```

- Now pass `--list=list.txt` to the script, i.e `$ python3 spotdl.py --list=list.txt`
and it will start downloading songs mentioned in `list.txt`.

- You can stop downloading songs by hitting `ctrl+c`, the script will automatically
resume from the song where you stopped it the next time you want to download
the songs present in `list.txt`.

- Songs that are already downloaded will prompt you to overwrite or skip. This behavior can be changed by
passing `--overwrite {prompt,skip,force}`.

#### Download by Playlist Link

- You can copy the Spotify URL of the playlist and pass it in `--playlist` option.
Note: This method works for public as well as private playlists.

For example

- `$ python3 spotdl.py --playlist https://open.spotify.com/user/nocopyrightsounds/playlist/7sZbq8QGyMnhKPcLJvCUFD`

- The script will load all the tracks from the playlist into `<playlist_name>.txt`

- Then you can simply run `$ python3 spotdl.py --list=<playlist_name>.txt`
to download all the tracks.

#### Download by Album Link

- You can copy the Spotify URL of the album and pass it in `--album` option.

For example

- `$ python3 spotdl.py --album https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg`

- The script will load all the tracks from the album into `<album_name>.txt`

- Then you can simply run `$ python3 spotdl.py --list=<album_name>.txt`
to download all the tracks.

#### Download by Username

- You can also load songs using Spotify username if you don't have the playlist URL.
(Open profile in Spotify, click on the three little dots below name,
"Share", "Copy to clipboard", paste last numbers or text into command-line:
`https://open.spotify.com/user/0123456790`)

- Try running `python3 spotdl.py -u <your_username>`, it will (only) show all your
public playlists (which excludes collaborative and private playlists).

- Once you select the one you want to download, the script will load all the tracks
from the playlist into `<playlist_name>.txt`.

- Run `$ python3 spotdl.py --list=<playlist_name>.txt` to download all the tracks.

#### Specify the Target Directory

If you don't want to download all the songs to the `Music/` folder relative to the
`spotdl.py` script, you can use the `-f`/`--folder` option.
E.g. `$ python3 spotdl.py -s "adele hello" -f "/home/user/Music/"`.
This works with both relative and absolute paths.

## Config File

At first run, this tool will generate a `config.yml` in root directory
of the code base with default options. You can then modify `config.yml`
to override any default options.

Also note that config options are overridden by command-line arguments.

#### Specify the Custom Config File Path

If you want to use custom `.yml` configuration instead of the default one, you can use `-c`/`--config` option.
E.g. `$ python3 spotdl.py -s "adele hello" -c "/home/user/customConfig.yml"`

## [Docker Image](https://hub.docker.com/r/ritiek/spotify-downloader/)
[![Docker automated build](https://img.shields.io/docker/automated/jrottenberg/ffmpeg.svg)](https://hub.docker.com/r/ritiek/spotify-downloader)
[![Docker pulls](https://img.shields.io/docker/pulls/ritiek/spotify-downloader.svg)](https://hub.docker.com/r/ritiek/spotify-downloader)

We also provide the latest docker image on [DockerHub](https://hub.docker.com/r/ritiek/spotify-downloader/).

- Pull (or update) the image with `$ docker pull ritiek/spotify-downloader`.

- Run it with `$ docker run --rm -it -v $(pwd):/music ritiek/spotify-downloader <arguments>`.

- The container will download music and write tracks in your current working directory.

**Example - Downloading a Playlist**

```
$ docker run --rm -it -v $(pwd):/music ritiek/spotify-downloader -p https://open.spotify.com/user/nocopyrightsounds/playlist/7sZbq8QGyMnhKPcLJvCUFD
$ docker run --rm -it -v $(pwd):/music ritiek/spotify-downloader -l ncs-releases.txt
```

### Exit Codes

- `0` - Success
- `1` - Unknown error
- `2` - Command line error (e.g. invalid args)
- `3` - `KeyboardInterrupt`
- `10` - Invalid playlist URL
- `11` - Playlist not found

## Contributing

Check out [CONTRIBUTING.md](CONTRIBUTING.md) for more info.

## Running Tests

```
$ python3 -m pytest test
```

Obviously this requires the `pytest` module to be installed.

## Disclaimer

Downloading copyright songs may be illegal in your country.
This tool is for educational purposes only and was created only to show
how Spotify's API can be exploited to download music from YouTube.
Please support the artists by buying their music.

## License

[![License](https://img.shields.io/github/license/ritiek/spotify-downloader.svg)](https://github.com/ritiek/spotify-downloader/blob/master/LICENSE)
