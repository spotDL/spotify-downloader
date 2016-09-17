# Spotify-Downloader

• This little python script allows downloading songs from Spotify just by entering the song's HTTP link or its URI.
• You can also download a song by entering its artist and song name.
• Downloading a song using spotify link will automatically fix its meta-tags and add a nice a albumart to the song.

That's how your Music library will look like!
<img src="http://i.imgur.com/Gpch7JI.png" alt="Drawing" style="width: 20px;"/>
<img src="http://i.imgur.com/5vhk3HY.png" alt="Drawing" style="width: 20px;"/>
<img src="http://i.imgur.com/RDTCCST.png" alt="Drawing" style="width: 20px;"/>
## Dependencies:

```
pip install mechanize
pip install BeautifulSoup4
pip install pafy
pip install spotipy
pip install eyed3
```

You'll also need to install avconv:
```
sudo apt-get install liabav-tools
```

## Installation & Usage:
```
cd ~
git clone https://github.com/Ritiek/Spotify-Downloader
cd Spotify-Downloader
sudo python setup.py install
```
Use ```spotdl``` to launch the script.

## Commands usable in script:
```
• play - will play the last song downloaded using default music player
• exit - exit the script
• list - downloads songs from list.txt
• lyrics - will print out the lyrics for last downloaded song.
```

## Downloading Music from Spotify:

• To download music from spotify just copy the song's HTTP link or URI and paste it in the script.
• You can also create ```list.txt``` in the folder where script is placed and add all the song you want to download (either by name or its spotify link).
• Use the command ```list``` in the script to start downloading the list.

## Disclaimer:

Downloading copyright songs may be illegal in your country. Please support the artists by buying their music.

## License:

```The MIT License```
