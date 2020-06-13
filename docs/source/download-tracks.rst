Download Tracks
***************

This page documents all the available ways for downloading tracks.


Download a Track
================

You can download single tracks using the *\--song* argument. Here's
what all parameters can be passed to *\--song*.

Download by Name
----------------

**For example:**

- We want to download *Fade* by *Alan Walker*, run the command:

    .. CODE::

        $ spotdl --song "alan walker fade"

- The tool will automatically look for the best matching song and
  download it in the current working directory.

- It will also encode the track to an mp3 while it is being downloaded.

- Once it has both been downloaded and encoded, it will proceed to
  write metadata on this track.

.. TIP::
    The `\--song` parameter can also accept multiple tracks like so:

    .. CODE::

        $ spotdl --song "alan walker fade" "tobu candyland"


Download by Spotify URI
-----------------------

.. IMPORTANT::
    It is recommened to use Spotify URIs for downloading tracks as it
    guarantees that the track exists on Spotify which allows the tool
    to always fetch the accurate metadata.

**For example:**

- We want to download the same song (i.e: *Fade* by *Alan Walker*) but using
  Spotify URI this time that looks like `https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l`.

.. HINT::
    You can copy this URI from your Spotify desktop or mobile app by
    right clicking or long tap on the song and copy HTTP link.

- Then run this command:

    .. CODE::

        $ spotdl --song https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l

- Just like before, the track will be both downloaded and encoded, but
  since we used the Spotify URI this time, the tool is guaranteed to
  fetch the correct metadata.


Download by YouTube Link
------------------------

- You can copy the YouTube URL or ID of a video and pass it in `-s` argument.

**For example:**

- Run the command:

    .. CODE::

        $ spotdl -s https://www.youtube.com/watch?v=lc4Tt-CU-i0

- It should download *2SCOOPS* by *Donuts*.


Download from File
==================

You can also pass a file filled with tracks to the tool for download.
This allows for some features not available with passing multiple
tracks to *\--song* argument.

**For example:**

- We want to download *Fade* by *Alan Walker*, *Sky High* by *Elektromania*
  and *Fire* by *Elektromania* just using a single command.

- Let's suppose, we have the Spotify link for only *Fade* by *Alan Walker* and
  *Fire by Elektromania*.

- Make a *list.txt* anywhere on your drive and add all the songs you want to
  download, in our case they are:

    .. CODE::

        https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l
        elektromania sky high
        https://open.spotify.com/track/0fbspWuEdaaT9vfmbAZr1C

- Now pass *\--list=/path/to/list.txt* to the script, i.e:

    .. CODE::

        $ spotdl --list=/path/to/list.txt

  and it will start downloading songs mentioned in *list.txt*.

- The tool will remove the track from the list file once it gets
  downloaded, and then continue to the next track.

.. NOTE::
    Songs that are already downloaded will prompt you to overwrite or
    skip. This default behaviour can be changed by passing one of
    *\--overwrite {prompt,skip,force}*.

.. TIP::
    In case you accidentally interrupt the download, you can always
    re-launch the same command back and the script will continue
    downloading the tracks from where it left off.


Download Playlists and Albums
=============================

For downloading playlists or albums, you need to first load all the
tracks into a file and then pass this file to the tool for download.

Download by Playlist URI
------------------------

- You can copy the Spotify URI of the playlist and pass it in *\--playlist* argument.

.. NOTE::
    This method works for both public as well as private playlists.

**For example:**

- To download the playlist
  *https://open.spotify.com/user/nocopyrightsounds/playlist/7sZbq8QGyMnhKPcLJvCUFD*,
  run the command:

    .. CODE::

        $ spotdl --playlist https://open.spotify.com/user/nocopyrightsounds/playlist/7sZbq8QGyMnhKPcLJvCUFD

- This will load all the tracks from the playlist into *<playlist_name>.txt*.

- Now run the command:

    .. CODE::

        $ spotdl --list=<playlist_name>.txt

  to download all the tracks (see `#download-from-file <#download-from-file>`_ for more info).

.. TIP::
    By default, the tracks are written to *<playlist_name>.txt*. You can
    specify a custom target file by passing *\--write-to <filename.txt>*.


Download by Album URI
---------------------

- You can copy the Spotify URI of the album and pass it in *\--album* argument.

**For example:**

- To download the album
  *https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg*,
  run the command:

    .. CODE::

        $ spotdl --album https://open.spotify.com/album/499J8bIsEnU7DSrosFDJJg

- The script will load all the tracks from the album into *<album_name>.txt*.

- Now run the command:

    .. CODE::

        $ spotdl --list=<album_name>.txt

  to download all the tracks (see `#download-from-file <#download-from-file>`_ for more info).


Download by Username
--------------------

- You can also load songs using Spotify username if you don't have the playlist URL.

.. HINT::
    If you don't know the Spotify username. Open the user's profile in
    Spotify, click on the three little dots below name -> *Share* ->
    *Copy to clipboard*. Now you'll have something like this in your
    clipboard: *https://open.spotify.com/user/12345abcde*.
    The last numbers or text is the username.

- Run the command:

    .. CODE::

        $ spotdl -u <your_username>

- Once you select the one you want to download, the script will load all the tracks
  from the playlist into *<playlist_name>.txt*.

- Now run the command:

    .. CODE::

        $ spotdl --list=<playlist_name>.txt

  to download all the tracks (see `#download-from-file <#download-from-file>`_ for more info).

.. NOTE::
    When using the *username* to display the playlists, only public
    playlists will be delivered. Collaborative and private playlists
    will not be delivered.


Download by Artist URI
----------------------

- You can copy the Spotify URI of the artist and pass it in *\--all-albums* argument.

**For example:**

- To download all albums of the artist
  *https://open.spotify.com/artist/1feoGrmmD8QmNqtK2Gdwy8*,
  run the command:

    .. CODE::

        $ spotdl --all-albums https://open.spotify.com/artist/1feoGrmmD8QmNqtK2Gdwy8

- The script will load all the tracks from artist's available albums into *<artist_name>.txt*

- Now run the command:

    .. CODE::

        $ spotdl --list=<artist_name>.txt

  to download all the tracks (see `#download-from-file <#download-from-file>`_ for more info).

