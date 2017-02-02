# Spotify-Downloader

◘ This little python script allows downloading songs from Spotify by looking for them on YouTube just by entering the song's HTTP link or its URI in an MP3 format.

◘ You can also download a song by entering its artist and song name.

◘ Downloading a song using spotify link will automatically fix its meta-tags and add a nice a albumart to the song.

That's how your Music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290">
<img src="http://i.imgur.com/5vhk3HY.png" width="290">
<img src="http://i.imgur.com/RDTCCST.png" width="290">

◘ If you cloned this repository before [266586a](https://github.com/Ritiek/Spotify-Downloader/commit/266586a2778f2cc2828079ed45699fe434ac5f14) and can't see the meta tags with Windows Media Player and other old players; manipulate and run the below snippet accordingly:

```
import eyed3
import os
for x in os.listdir('/home/pi/Spotify-Downloader/Music/'):
  if x.endswith('.mp3'):
    audiofile = eyed3.load('/home/pi/Spotify-Downloader/Music/' + x)
    audiofile.tag.save(version=(2,3,0))
```

Feel free to report issues and fork this repository!

## Installation & Usage:

#### Debian, Ubuntu, Linux & Mac:
```
cd
git clone https://github.com/Ritiek/Spotify-Downloader
cd Spotify-Downloader
sudo pip install -r requirements.txt
```
You'll also need to install avconv:

`sudo apt-get install libav-tools`

Use `sudo python spotdl.py` to launch the script.

#### Windows:

Assuming you have python (2.7.12 or higher, python 3 is not supported currently) already installed..

Download Libav-Tools for windows: https://builds.libav.org/windows/release-gpl/libav-x86_64-w64-mingw32-11.7.7z.
Copy all the contents of bin folder (of avconv) to Scripts folder (in your python's installation directory)

Download the zip file of this repository and extract its contents in your python's installation folder as well.
Shift+right-click on empty area and open cmd and type:

`"Scripts/pip.exe" install -r requirements.txt`

Now to run the script type:

`python.exe spotdl.py`

(you can create a batch file shortcut to run the script just by double-click anytime)

## Instructions for Downloading Songs:

- First launch the script using the above command as mentioned for your OS.

- If you want to skip the conversion process and meta-tags, run the script by passing `-n` or `--no-convert` option:
`sudo python spotdl.py -n` or `python.exe spotdl.py -n` depending on your OS.
[NOTE: This option will also skip meta-tags as .m4a cannot hold meta-tags]

- Use `-h` option to see full list of supported options.

#### Downloading by Name:

For example:

◘ We want to download Hello by Adele, simply run the script and type `adele hello`.

◘ The script will automatically look for the best matching song and download it in the folder `Music/` placed in your current directory.

◘ It will now convert the song to an mp3.

◘ Now, if we want to check it out the lyrics of that song, just type `lyrics` in the script and it should print out the lyrics for any last downloaded song.

◘ Okay, lets play the song now. Just type `play` in the script.

#### Downloading by Spotify Link:

For example:

◘ We want to download the same song (i.e: Hello by Adele) but using Spotify Link this time that looks like  `http://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7`, you can copy it from your Spotify desktop or mobile app by right clicking or long tap on the song and copy HTTP link.

◘ Now simply paste this link after running the script, it should download Hello by Adele.

◘ Just like before, it will again convert the song to an mp3.

◘ Now, that we have used a Spotify link to download the song, the script will automatically fix the meta-tags and add an album-art to the song.

◘ Similarly, we can now check out its lyrics or play it.

◘ Just type `exit` to exit out of the script.

#### What if we want to download multiple songs at once?

For example:

◘ We want to download Hello by Adele, The Nights by Avicci and 21 Guns by Green Day just using a single command.

Also this time we have the Spotify link only for Hello by Adele but not for other two songs.

No problem!

◘ Just make a list.txt by running the following commands:

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

◘ Now just run the script and type ```list```, it will automatically start downloading the songs you provided in `list.txt`.

◘ You can stop downloading songs by hitting `ctrl+c`, the script will automatically resume from the song where you stopped it the next time you want to download the songs using `list`.

◘ To download all songs in your playlist, just select all the songs `ctrl+a` in Spotify desktop app, copy them `ctrl+c` and paste `ctrl+v` in `list.txt`.

## Brief info on Commands:
```
• play - will play the last song downloaded using mplayer
• list - downloads songs from list.txt
• lyrics - will print out the lyrics for last downloaded song
• exit - exit the script
```

## Disclaimer:

Downloading copyright songs may be illegal in your country. Please support the artists by buying their music.

## License:

```The MIT License```
