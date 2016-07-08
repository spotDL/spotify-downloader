# YTMusic

My first GitHub Repository (sorry for any mistakes)

This python script allows downloading songs from youtube by just entering the name of the song
and the artist in mp3 extension.


DEPENDENCIES:

```
pip install mechanize
pip install bs4
pip install pafy
```
```
sudo apt-get install ffmpeg
or download from https://ffmpeg.zeranoe.com/builds/ for windows and place the ffmpeg.exe in your script folder
```

COMMANDS YOU CAN USE IN THE SCRIPT:
```
2. play - will play the last song downloaded using default music player
3. gg - exit the script
4. spotify - downloads songs from spotify playlist (see below:)
```

DOWNLOADING MUSIC FROM SPOTIFY:

1. To download music from spotify playlists goto http://www.playlist-converter.net/ and login to your
spotify account and choose the playlist you want to download. Let it grab the tracks and then click
on ```Export to free text```.
2. Copy the songs list and create a new text file ```spotify.txt``` in your Music directory and paste the
songs list.
3. Use the command ```spotify``` in the script to start downloading the list.

KNOWN BUGS (pls help me fix them):

1. Fails to download songs containing accents (that is, characters like 'Ø' in song like 'BØRNS Seeing Stars')
in the Youtube's video title.
