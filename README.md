# YTMusic [Alpha Release]

My first GitHub Repository (sorry for any mistakes)

This python script allows downloading songs instantly by just entering the name of the song
and the artist.

![Alt text](http://i.imgur.com/lWyA2pj.png "Testing")

# Dependencies:

```
pip install mechanize
pip install bs4
pip install pafy
```
[OPTIONAL] If you want to convert downloaded music to mp3 (from m4a) install avconv:
```
sudo apt-get install libav-tools
or download from https://libav.org/download/ for windows
```

# Installation & Usage:
```
git clone https://github.com/Ritiek/YTMusic
cd YTMusic
sudo python setup.py install
```
or you can also install from pypi using:
```
pip install YTMusic
```
Run it using:
```
YTMusic
```

# Commands that can be used in the script:
```
1. play - will play the last song downloaded using default music player
2. spotify - downloads songs from spotify playlist (see below:)
3. convert - will convert all your m4a songs into mp3
3. exit - exit the script
```

# Downloading Music from Spotify:

1. To download music from spotify playlists goto http://www.playlist-converter.net/ and login to your
spotify account and choose the playlist you want to download. Let it grab the tracks and then click
on ```Export to free text```.
2. Copy the songs list and create a new text file ```spotify.txt``` in your Music directory and paste the
songs list.
3. Use the command ```spotify``` in the script to start downloading the list.

# Known bugs:

1. Fails to download songs containing accents (that is, characters like ```Ø``` in song like ```BØRNS Seeing Stars```)
in the Youtube's video title.

# Disclaimer:

Downloading Copyright Music may be illegal in you country. Please support the artists by buying their Music.
