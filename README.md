# Spotify-Downloader

[![Build Status](https://travis-ci.org/ritiek/spotify-downloader.svg?branch=master)](https://travis-ci.org/ritiek/spotify-downloader)

- Downloads songs from YouTube in an MP3 format by using Spotify's HTTP link.

- Can also download a song by entering its artist and song name (in case if you don't have the Spotify's HTTP link for some song).

- Automatically fixes song's meta-tags which include:

  - Title
  - Artist
  - Album
  - Album art
  - Album artist
  - Genre
  - Track number
  - Disc number
  - Release date
  - And some more...

- Works straight out of the box and does not require to generate or mess with your API keys.

That's how your Music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290"><img src="http://i.imgur.com/5vhk3HY.png" width="290"><img src="http://i.imgur.com/RDTCCST.png" width="290">

## Reporting Issues

- Search for your problem in the [issues section](https://github.com/Ritiek/spotify-downloader/issues?utf8=%E2%9C%93&q=) before opening a new ticket. It might be already answered and save us time. :smile:

- Provide as much information possible when opening your ticket.

## Installation & Usage

<img src="http://i.imgur.com/Dg8p9up.png" width="600">

- **This version supports Python 3**, Python 2 compatibility was dropped because of the way it deals with unicode. If you need to use Python 2 though, check out the `python2` branch.

- Note: `play` and `lyrics` commands have been deprecated in the current brach since they were not of much use and created unnecessary clutter. You can still get them back by using `old` branch though.

### Debian, Ubuntu, Linux & Mac

```
cd
git clone https://github.com/ritiek/spotify-downloader
cd spotify-downloader
pip install -U -r requirements.txt
```

You'll also need to install FFmpeg for conversion (use `--avconv` if you'd like to use that instead):

Linux: `sudo apt-get install ffmpeg`

Mac: `brew install ffmpeg --with-libmp3lame --with-libass --with-opus --with-fdk-aac`

If it does not install correctly, you may have to build it from source. For more info see https://trac.ffmpeg.org/wiki/CompilationGuide.

### Windows

Assuming you have Python 3 already installed and in PATH.

- Download and extract the [zip file](https://github.com/ritiek/spotify-downloader/archive/master.zip) from master branch.

- Download FFmpeg for Windows from [here](http://ffmpeg.zeranoe.com/builds/). Copy `ffmpeg.exe` from `ffmpeg-xxx-winxx-static\bin\ffmpeg.exe` to PATH (usually C:\Windows\System32\) or just place it in the root directory extracted from the above step.

- Open `cmd` and type `pip install -U -r requirements.txt` to install dependencies.

## Instructions for Downloading Songs

- For all available options, run `python spotdl.py --help`.

```
usage: spotdl.py [-h] (-s SONG | -l LIST | -p PLAYLIST | -u USERNAME) [-m]
                 [-nm] [-a] [-f FOLDER] [-v] [-i INPUT_EXT] [-o OUTPUT_EXT]

Download and convert songs from Spotify, Youtube etc.

optional arguments:
  -h, --help            show this help message and exit
  -s SONG, --song SONG  download song by spotify link or name (default: None)
  -l LIST, --list LIST  download songs from a file (default: None)
  -p PLAYLIST, --playlist PLAYLIST
                        load songs from playlist URL into <playlist_name>.txt
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
                        Music/)
  -v, --verbose         show debug output (default: False)
  -i INPUT_EXT, --input_ext INPUT_EXT
                        prefered input format .m4a or .webm (Opus) (default:
                        .m4a)
  -o OUTPUT_EXT, --output_ext OUTPUT_EXT
                        prefered output extension .mp3 or .m4a (AAC) (default:
                        .mp3)
```

#### Download by Name

For example

- We want to download Hello by Adele, simply run `python spotdl.py --song "adele hello"`.

- The script will automatically look for the best matching song and download it in the folder `Music/` placed in the root directory of the code base.

- It will now convert the song to an mp3 and try to fix meta-tags and album-art by looking up on Spotify.

#### Download by Spotify Link (Recommended)

For example

- We want to download the same song (i.e: Hello by Adele) but using Spotify Link this time that looks like  `http://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7`, you can copy it from your Spotify desktop or mobile app by right clicking or long tap on the song and copy HTTP link.

- Run `python spotdl.py --song http://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7`, it should download Hello by Adele.

- Just like before, it will again convert the song to an mp3 but since we used a Spotify HTTP link, the script is guaranteed to fetch the correct meta-tags and album-art.

#### Download multiple songs at once

For example

- We want to download `Hello by Adele`, `The Nights by Avicci` and `21 Guns by Green Day` just using a single command.

Let's suppose, we have the Spotify link for only `Hello by Adele` and `21 Guns by Green Day`.

No problem!

- Just make a `list.txt` in the same folder as the script and add all the songs you want to download, in our case it is

(if you are on Windows, just edit `list.txt` - i.e `C:\Python36\spotify-downloader-master\list.txt`)

```
https://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7
the nights avicci
http://open.spotify.com/track/64yrDBpcdwEdNY9loyEGbX
```

- Now pass `--list=list.txt` to the script, i.e `python spotdl.py --list=list.txt` and it will start downloading songs mentioned in `list.txt`.

- You can stop downloading songs by hitting `ctrl+c`, the script will automatically resume from the song where you stopped it the next time you want to download the songs present in `list.txt`.

- Songs that are already downloaded will be skipped and not be downloaded again.

#### Download playlists

- You can copy the Spotify URL of the playlist and pass it in `--playlist` option.

For example

- `python spotdl.py --playlist https://open.spotify.com/user/camillazi/playlist/71MXqcSOKCxsLNtRvONkhF`

- The script will load all the tracks from the playlist into `<playlist_name>.txt`

- Then you can simply run `python spotdl.py --list=<playlist_name>.txt` to download all the tracks.

#### Download playlists by username

- You can also load songs using Spotify username if you don't have the playlist URL. (Open profile in Spotify, click on the three little dots below name, "Share", "Copy to clipboard", paste last numbers into command-line: `https://open.spotify.com/user/0123456790`)

- Try running `python spotdl.py -u <your_username>`, it will show all your public playlists.

- Once you select the one you want to download, the script will load all the tracks from the playlist into `<playlist_name>.txt`.

- Run `python spotdl.py --list=<playlist_name>.txt` to download all the tracks.

#### Specify the target directory

If you don't want to download all the songs to the `Music/` folder relative to the `spotdl.py` script, you can use the `-f`/`--folder` option. E.g. `python spotdl.py -s "adele hello" -f "/home/user/Music/"`. This works with both relative and absolute paths.

## Running tests

```
python -m pytest test
```

Obviously this requires the `pytest` module to be installed. 

## Disclaimer

Downloading copyright songs may be illegal in your country. This tool is for educational purposes only and was created only to show how Spotify's API can be exploited to download music from YouTube. Please support the artists by buying their music.

## License

```The MIT License```
