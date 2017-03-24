# Spotify-Downloader

- Download songs from YouTube in an MP3 format by using Spotify's HTTP link.

- Can also download a song by entering its artist and song name (in case if you don't have the Spotify's HTTP link for some song).

- Downloading a song using a Spotify link will automatically fix meta-tags and add a nice albumart to the song.

<br>

That's how your Music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="280">
<img src="http://i.imgur.com/5vhk3HY.png" width="280">
<img src="http://i.imgur.com/RDTCCST.png" width="280">

#### Have an Issue?

- Search for your problem in the [Issues section](https://github.com/Ritiek/Spotify-Downloader/issues) before opening a new ticket. It might be already answered and save you and me some time :D

- Provide as much information possible when opening your ticket.

## Installation & Usage:

### Debian, Ubuntu, Linux & Mac:
```
cd
git clone https://github.com/Ritiek/Spotify-Downloader
cd Spotify-Downloader
sudo pip install -U -r requirements.txt
```
You'll also need to install avconv:

`sudo apt-get install libav-tools`

Use `sudo python spotdl.py` to launch the script.

### Windows:

Assuming you have python (2.7.12 or higher, python 3 is not supported currently) already installed..

- Download Libav-Tools for windows: https://builds.libav.org/windows/release-gpl/libav-x86_64-w64-mingw32-11.7.7z. Copy all the contents of bin folder (of avconv) to Scripts folder (in your python's installation directory)

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

- It will now convert the song to an mp3.

- Now, if we want to check it out the lyrics of that song, just type `lyrics` in the script and it should print out the lyrics for any last downloaded song.

- Okay, lets play the song now. Just type `play` in the script.

#### Downloading by Spotify Link:

For example:

- We want to download the same song (i.e: Hello by Adele) but using Spotify Link this time that looks like  `http://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7`, you can copy it from your Spotify desktop or mobile app by right clicking or long tap on the song and copy HTTP link.

- Now simply paste this link after running the script, it should download Hello by Adele.

- Just like before, it will again convert the song to an mp3.

- Now, that we have used a Spotify link to download the song, the script will automatically fix the meta-tags and add an album-art to the song.

- Similarly, we can now check out its lyrics or play it.

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

add all the songs you want to download, in our case it is:

```
https://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7
the nights avicci
21 guns green day
```

- Now just run the script and type ```list```, it will automatically start downloading the songs you provided in `list.txt`.

- You can stop downloading songs by hitting `ctrl+c`, the script will automatically resume from the song where you stopped it the next time you want to download the songs using `list`.

- To download all songs in your playlist, just select all the songs `ctrl+a` in Spotify desktop app, copy them `ctrl+c` and paste `ctrl+v` in `list.txt`.

## Brief info on Commands:
```
• play - will play the last song downloaded using mplayer
• list - downloads songs from list.txt
• lyrics - will print out the lyrics for last downloaded song
• exit - exit the script
```

## Disclaimer:

Downloading copyright songs may be illegal in your country. This tool is for educational purposes only and was created only to show how Spotify's API can be exploited to download music from YouTube. Please support the artists by buying their music.

## License:

```The MIT License```
