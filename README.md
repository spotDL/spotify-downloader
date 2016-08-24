# YTMusic

My first GitHub Repository (sorry for any mistakes)

This python script allows downloading songs instantly by just entering the name of the song and the artist or its Spotify HTTP or URI link.

![alt tag](https://camo.githubusercontent.com/3f4374e9ad1b1ec21994cd564385ec8501751b4f/687474703a2f2f692e696d6775722e636f6d2f6c57794132706a2e706e67)
## Dependencies:
```
pip install mechanize
pip install BeautifulSoup4
pip install pafy
pip install spotipy
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
• exit - exit the script
```

## Downloading Music from Spotify:
![alt tag](https://camo.githubusercontent.com/f8a671460df2d56ec52701db69c6c5c3ca685e94/687474703a2f2f692e696d6775722e636f6d2f3064716c59707a2e706e67)

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
