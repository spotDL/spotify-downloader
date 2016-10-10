# Spotify-Downloader

◘ This little python script allows downloading songs from Spotify just by entering the song's HTTP link or its URI in an MP3 format.

◘ You can also download a song by entering its artist and song name.

◘ Downloading a song using spotify link will automatically fix its meta-tags and add a nice a albumart to the song.

That's how your Music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290">
<img src="http://i.imgur.com/5vhk3HY.png" width="290">
<img src="http://i.imgur.com/RDTCCST.png" width="290">

Feel free to report issues and fork this repository!

## Installation & Usage:

#### Debian, Ubuntu, Linux & Mac:
```
cd
git clone https://github.com/Ritiek/Spotify-Downloader
cd Spotify-Downloader
sudo pip install -r requirements.txt
sudo python setup.py install
```
You'll also need to install avconv:
```
sudo apt-get install libav-tools
```
Use ```spotdl``` to launch the script.

#### Windows:

Assuming you have python (2.7.12 or higher, python 3 is not supported currently) already installed..

Download Libav-Tools for windows: https://builds.libav.org/windows/release-gpl/libav-x86_64-w64-mingw32-11.7.7z.
Copy all the contents of bin folder (of avconv) to Scripts folder (in your python's installation directory)

Download the zip file of this repository and extract its contents in your python's installation folder as well.
Shift+right-click on empty area and open cmd and type:
```
"Scripts/pip.exe" install -r requirements.txt
python.exe setup.py install
```
Now to run the script type:
```
python.exe Scripts/spotdl.py
```
(you can create a batch file to run the script just by double-click everytime)

## Step by step Instructions for Downloading songs:

#### Downloading by Name:

For example:

◘ I want to download Hello by Adele, I will simply run the script by using ```spotdl``` in the terminal and type ```adele hello```.

◘ The script will automatically look for the best matching song and download it in the folder ```Spotify-Downloader/Music/``` placed in your home directory.

◘ It will now convert the song to an mp3.

◘ Now, if we want to check it out the lyrics of that song, just type ```lyrics``` in the script and it should print out the lyrics for any last downloaded song.

◘ Okay, lets play the song now. Just type ```play``` in the script.

#### Downloading by Spotify Link:

For example:

◘ I want to download the same song (i.e: Hello by Adele) but using Spotify Link this time that looks like  ```http://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7```, you can copy it from your Spotify desktop or mobile app by right clicking or long tap on the song and copy HTTP link.

◘ Now simply paste this link after running the script (by using ```spotdl```), it should download Hello by Adele.

◘ Just like before, it will again convert the song to an mp3.

◘ Now, that we have used a Spotify link to download the song, the script will automatically fix the meta-tags and add an album-art to the song.

◘ Similarly, we can now check out its lyrics or play it.

◘ Just type ```exit``` to exit out of the script.

#### What if we want to download multiple songs at once?

For example:

◘ I want to download Hello by Adele, The Nights by Avicci and 21 Guns by Green Day just using a single command.

Also this time we know the Spotify link only for Hello by Adele but not for other two songs.

No problem!

◘ Just make a list.txt by running the following commands:

```
cd ~
cd Spotify-Downloader/Music
sudo nano list.txt
```
(or simply edit C:\Python27\Music\list.txt to add the songs and save it)

add all the songs you want to download, in our case it is:

```
https://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7
the nights avicci
21 guns green day
```

Now press ```ctrl+o```, ```y``` and ```ctrl+x``` to save and exit the nano text editor.

◘ Now just run the script again by ```spotdl``` and type ```list```, it will automatically start downloading the songs you provided in list.txt

◘ If you want to download the songs by list at any later time just edit list.txt by ```sudo nano Spotify-Downloader/Music/list.txt``` (assuming you're in you home directory) and use ```list``` in the script.

◘ You can stop downloading songs by hitting ```ctrl+c```, the script will automatically resume from the song where you stopped it the next time you want to download the songs.

## Brief info on Commands:
```
• play - will play the last song downloaded using mplayer
• list - downloads songs from list.txt
• lyrics - will print out the lyrics for last downloaded song.
• exit - exit the script
```

## Disclaimer:

Downloading copyright songs may be illegal in your country. Please support the artists by buying their music.

## License:

```The MIT License```
