# YTMusic

My first GitHub Repository (sorry for any mistakes)

This python script allows downloading songs instantly by just entering the name of the song and the artist.
![alt tag](https://camo.githubusercontent.com/3f4374e9ad1b1ec21994cd564385ec8501751b4f/687474703a2f2f692e696d6775722e636f6d2f6c57794132706a2e706e67)
## Dependencies:
```
pip install mechanize
pip install bs4
pip install pafy
```
[OPTIONAL] If you want to convert downloaded music to mp3 (from m4a) install avconv for linux or ffmpeg from https://ffmpeg.zeranoe.com/builds/ for windows and then place the ffmpeg.exe in your script folder:
```
sudo apt-get install libav-tools
or download from https://ffmpeg.zeranoe.com/builds/ for windows
```
## Installation & Usage:
```
git clone https://github.com/Ritiek/YTMusic
cd YTMusic
sudo python YTMusic.py
```
or you can also install from pypi using:
```
pip install YT_Music
```
Run it using:
```
YTMusic
```
## Commands that can be used in the Script:
```
• play - will play the last song downloaded using default music player
• spotify - downloads songs from spotify playlist (see below:)
• convert - will convert all your m4a songs into mp3
• exit - exit the script
```

## Downloading Music from Spotify:
![alt tag](https://camo.githubusercontent.com/f8a671460df2d56ec52701db69c6c5c3ca685e94/687474703a2f2f692e696d6775722e636f6d2f3064716c59707a2e706e67)
• To download music from spotify playlists goto http://www.playlist-converter.net/ and login to your spotify account and choose the playlist you want to download. Let it grab the tracks and then click on Export to free text.

• Copy the songs list and create a new text file spotify.txt in your Music directory and paste the songs list.
```
cd YTMusic/Music
sudo nano spotify.txt
[paste your songs here then ctrl+o, enter, ctrl+x]
sudo chmod 775 spotify.txt
```

• Use the command spotify in the script to start downloading the list.

## Disclaimer:
Downloading Copyright Music may be illegal in your country. Please support the artists by buying their Music.
