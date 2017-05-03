# Spotify-Downloader

- Downloads songs from YouTube in an MP3 format by using Spotify's HTTP link.

- Can also download a song by entering its artist and song name (in case if you don't have the Spotify's HTTP link for some song).

- Automatically fixes song's meta-tags.

<br>

That's how your Music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290"><img src="http://i.imgur.com/5vhk3HY.png" width="290"><img src="http://i.imgur.com/RDTCCST.png" width="290">

#### Have an Issue?

- Search for your problem in the [Issues section](https://github.com/Ritiek/Spotify-Downloader/issues) before opening a new ticket. It might be already answered and save you and me some time :D

- Provide as much information possible when opening your ticket.

## Installation & Usage:

This version supports both Python2 and Python3.
<br>

### Debian, Ubuntu, Linux & Mac:

```
cd
git clone https://github.com/Ritiek/Spotify-Downloader
cd Spotify-Downloader
sudo pip install -U -r requirements.txt
```
You'll also need to install avconv:

`sudo apt-get install libav-tools` (`brew install libav` for Mac)

Use `sudo python spotdl.py` to launch the script.

### Windows:

Assuming you have Python already installed..

- Download Libav-Tools for windows: https://builds.libav.org/windows/release-gpl/libav-x86_64-w64-mingw32-11.7.7z. Copy all the contents of bin folder (of libav) to Scripts folder (in your python's installation directory).

- Download the zip file of this repository and extract its contents in your python's installation folder as well.

Shift+right-click on empty area and open cmd and type:

`"Scripts/pip.exe" install -U -r requirements.txt`

Now to run the script type:

`python.exe spotdl.py`

(you can create a batch file shortcut to run the script just by double-click anytime)

## Instructions for Downloading Songs:

- Launch the script using the above command as mentioned for your OS.

- For available options, run `sudo python spotdl.py --help`.

#### Downloading by Name:

For example:

- We want to download Hello by Adele, simply run the script and type `adele hello`.

- The script will automatically look for the best matching song and download it in the folder `Music/` placed in your current directory.

- It will now convert the song to an mp3 and try to fix meta-tags and album-art by looking up on Spotify.

#### Downloading by Spotify Link (Recommended):

For example:

- We want to download the same song (i.e: Hello by Adele) but using Spotify Link this time that looks like  `http://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7`, you can copy it from your Spotify desktop or mobile app by right clicking or long tap on the song and copy HTTP link.

- Now simply paste this link after running the script, it should download Hello by Adele.

- Just like before, it will again convert the song to an mp3 but since we used a Spotify HTTP link, the script is guaranteed to fetch the correct meta-tags and album-art.

- Just type `exit` to exit out of the script.

#### What if we want to download multiple songs at once?

For example:

- We want to download Hello by Adele, The Nights by Avicci and 21 Guns by Green Day just using a single command.

Also this time we have the Spotify link only for Hello by Adele but not for other two songs.

No problem!

- Just make a list.txt by running the following commands:

```
cd
cd Spotify-Downloader
sudo nano list.txt
```
(if you are on windows, just edit `list.txt` - i.e `C:\Python27\list.txt`)

Add all the songs you want to download, in our case it is:

```
https://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7
the nights avicci
21 guns green day
```

- Now just run the script and type `list`, it will automatically start downloading the songs you provided in `list.txt`.

- You can stop downloading songs by hitting `ctrl+c`, the script will automatically resume from the song where you stopped it the next time you want to download the songs using `list` command.

- To download all songs in your playlist, just select all the songs `ctrl+a` in Spotify desktop app, copy them `ctrl+c` and paste `ctrl+v` in `list.txt`.

## Disclaimer:

Downloading copyright songs may be illegal in your country. This tool is for educational purposes only and was created only to show how Spotify's API can be exploited to download music from YouTube. Please support the artists by buying their music.

## License:

```The MIT License```
