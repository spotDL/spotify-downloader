# Modules

What are the various sub-packages and modules in spotDL? What do they do? Use this file a a
general look up for what you want to do.

# Index

1. [search](#The-search-package)
    - [provider](#provider)
    - [songObj](#songObj)
    - [spotifyClient](#spotifyClient)
    - [utils](#utils)

2. [download](#The-download-package)
    - [downloader]
    - [progressHandlers]

# The search package

This is where are the song searching, matching and related code is organized. The only two modules
you will ever need to use from this package if you intend to use spotDL as a library would be
`spotdl.search.songObj` and `spotdl.search.utils`, all the other module's functionality hook into
the aforementioned modules.

<br><br>

## provider

There are 2 modules here that return song details, the 'provider' module is one and 'spotifyClient'
is the other. The provider module queries YouTube Music and filters the results.

<br><br>

## songObj

This module houses the 'SongObj' class - something you will use often. The 'songObj' constitutes
the only way to pass around and query song details within spotDL. All top level code within the
'search' package returns 'songObjects' and all top level code within the 'download' package
take SongObj as inputs.

<br><br>

## spotDlApp

Serves as the boundary between platform (python) and application logic. This class allows us to setup
dependency injection (constructor injection, in this case) at the platform boundary, meaning we can test
our apps logic from the platform boundary to the network boundary.

<br><br>


## spotifyClient

The 'spotifyClient' module is a wrapper around `spotipy.Spotify` class. It provides flexibility
should we decide to switch to something other than spotipy.

<br><br>

## spotifyClientFactory

Builds an instance of the SpotifyClient class. Injecting this factory into the SpotDlApp class
provides us a unified means to create  instances both in production and in test, bolstering
confidence in our end-to-end configuration of the app.

<br><br>

## utils

Simple utilities to handle the times when you deal with album/playlist Url's and song queries by
name instead of track Url's.

<br><br>

# The download package