<!--- mdformat-toc start --slug=github --->

# Modules

What are the various sub-packages and modules in spotDL? What do they do? Use this file a
a general look up for what you want to do.

## Index

1. [search](#The-search-package)

   - [provider](#provider)
   - [songObj](#songObj)
   - [spotifyClient](#spotifyClient)
   - [utils](#utils)

2. [download](#The-download-package)

   - [downloader](#downloader)
   - [ffmpeg](#ffmpeg)
   - [progressHandlers](#progressHandlers)

## The search package

This is where are the song searching, matching and related code is organized. The only two
modules you will ever need to use from this package if you intend to use spotDL as a
library would be `spotdl.search.songObj` and `spotdl.search.utils`, all the other module's
functionality hook into the aforementioned modules.

### provider

There are 2 modules here that return song details, the 'provider' module is one and
'spotifyClient' is the other. The provider module queries YouTube Music and filters the
results.

### songObj

This module houses the 'SongObj' class - something you will use often. The 'songObj'
constitutes the only way to pass around and query song details within spotDL. All top
level code within the 'search' package returns 'songObjects' and all top level code within
the 'download' package take SongObj as inputs.

### spotifyClient

The 'spotifyClient' module is a wrapper around `spotipy.Spotify` class, it ensures that
there is only one instance of the `Spotify` class at runtime and that the same class is
shared across multiple 'internal name-spaces' instead of creating new clients each time.
Essentially, it implements a 'singleton' pattern.

### utils

Simple utilities to handle the times when you deal with album/playlist Url's and song
queries by name instead of track Url's.

______________________________________________________________________

## The download package

This is where are the downloading, converting, tagging and related code is organized. The
only two modules you will ever need to use from this package if you intend to use spotDL
as a library would be `spotdl.download.downloader` and `spotdl.download.ffmpeg`, all the
other module's functionality hook into the aforementioned modules.

### downloader

The downloader module is responsible for downloading the songs (from youtube if a match is
found), converting them to mp3 format and applying metadata.

### ffmpeg

The ffmpeg module contains functions to verify `ffmpeg` version and convert downloaded
songs to the `mp3` format.

### progressHandlers

The progressHandlers module handles the progress bar, download tracking and everything
related to what you see in the terminal.
