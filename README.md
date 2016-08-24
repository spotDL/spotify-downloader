# YTMusic

• This python script allows downloading songs instantly by just entering the name of the song and the artist or its Spotify HTTP or URI link.

• Downloading a song using a Spotify link will automatically fix song's meta-tags and add a nice cover-art to your song.

## Dependencies:
```
pip install requests
pip install mechanize
pip install BeautifulSoup4
pip install pafy
pip install spotipy
pip install eyed3
```
```
sudo apt-get install libav-tools
```
## Installation & Usage:
```
git clone https://github.com/Ritiek/YTMusic
cd YTMusic
sudo python setup.py install
```
Run it using:
```
YTMusic
```
## Commands that can be used in the Script:
```
• play - will play the last song downloaded using default music player
• list - downloads songs using from a list
• lyrics - prints out lyrics for last downloaded song
• exit - exit the script
```

## Downloading Music from Spotify:

• To download music from spotify, simply copy its HTTP or URI link and paste it in the script.

• You can also copy the songs list (names or HTTP or URI) and create a new text file ```list.txt``` in your Music directory and paste the songs list.
```
cd YTMusic/Music
sudo nano list.txt
[paste your songs here then ctrl+o, enter, ctrl+x]
sudo chmod 777 list.txt
```

• Use the command ```list``` in the script to start downloading the list.

## Disclaimer:
Downloading Copyright Music may be illegal in your country. Please support the artists by buying their Music.
