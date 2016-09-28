# Spotify-Downloader

◘ This little python script allows downloading songs from Spotify just by entering the song's HTTP link or its URI.

◘ You can also download a song by entering its artist and song name.

◘ Downloading a song using spotify link will automatically fix its meta-tags and add a nice a albumart to the song.

That's how your Music library will look like!

<img src="http://i.imgur.com/Gpch7JI.png" width="290">
<img src="http://i.imgur.com/5vhk3HY.png" width="290">
<img src="http://i.imgur.com/RDTCCST.png" width="290">

Feel free to report issues and send pull requests for new ideas!

## Dependencies:

Install required python packages
```
pip install -r requirements.txt
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

◘ I want to download the same song (i.e: Hello by Adele) but using Spotify Link this time that looks like ```https://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7```, you can copy it from your Spotify desktop or mobile app by right clicking or long tap on the song and copy HTTP link.

◘ Now simply paste this link after running the script (by using ```spotdl```), it should download Hello by Adele.

◘ Just like before, it will again convert the song to an mp3.

◘ Now, that we have used a Spotify link to download the song, the script will automatically fix the meta-tags and add an album-art to the song.

◘ Similarly, we can now check out its lyrics or play it.

◘ Just type ```exit``` to exit out of the script.

#### What if we want to download multiple songs at once?

For example:

◘ I want to download Hello by Adele, The Nights by Avicci and 21 Guns by Green Day just a single command.

Also this time we know the Spotify link only for Hello by Adele but not for other two songs.

No problem!

◘ Just make a list.txt by running the following commands:

```
cd ~
cd Spotify-Downloader/Music
sudo nano list.txt
```

add all the songs you want to download, in our case it is:

```
https://open.spotify.com/track/1MDoll6jK4rrk2BcFRP5i7
the nights avicci
21 guns green day
```

Now press ```ctrl+o```, ```y``` and ```ctrl+x``` to save and exit the nano text editor.
You'll have to give 775 permissions to the text file:

```
sudo chmod 775 list.txt
```
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
