# What is this document?

v3.0.0 of spotDL was found to be lacking in many ways. While it fixed many of the issues
its predecessor had, it brought with it, many issues of its own. Primarily, poor
access-control and unnecessary functionality.

To address the issues of mucked-up class's, functions, modules and unnecessary
functionality this project here on works on zero-base-accounting - if you can't justify
it's need, you don't build it. The purpose of various functions, modules and classes
will be listed here and adhered to strictly. This document then, represents the primary
source of truth as to the requirement and responsibility of each unit of code.

# Structure

module name > class or function name (class/function) > PUR(pose) and REA(son)

Purpose and Reason are fairly similar words. By purpose we mean just what that class or
function is meant to do, it's functionality. By Reason we mean justification as to why
that class/function should exist

<br><br>

# songObj

## songObj class

[PUR.] songObj is meant to serve dual purposes - to act as an ***exchange currency***
through out spotDL and as a central repository of all known details of a given song.

[REA.] A lot of what spotDL does requires passing around of various details about songs.
The songObj serves as a ***single-point-of-access*** to all the various details we
might seek. The eliminates the need to query the same info multiple times from a server
while eliminating any ambiguity as to code unit return types. It also allows a consistent
interface to song details thereby adding to simplicity.

<br><br>

# spotifyClient

## get function

[PUR.] Provide an abstaction layer between app and spotipy's Spotify instance.

[REA.] Allows more flexibility if we chose to swap out spotipy with something else.

# spotifyClientFactory

## build function

[PUR.] Builds an instance of our SpotifyClient class, given a clientId and clientSecret.

[REA.] Allows for shared configuration of the SpotifyClient class in prod and in tests.

<br><br>

# provider

## __query_and_simplify function

[PUR.] To query YouTube Music and extract details from their hopelessly nested responses

[REA.] Compartmentalize YouTube link matching. The whole search providing interface can
be jointed into one massive function but then, making changes would be unduly difficult.

## search_and_order function

[PUR.] To filter, and measure the likelihood of available YouTube Music results being the
songs the user is after

[REA.] Although YouTube Music's results are far better than YouTube's, it still relies on
an extent upon the user to select the best match according to what ever he/she/them is
searching for. A program can not identify the best match like a human being who would
identify the song by video thumbnail or album art. So we attempt to measure the extent
to which it is the same song as the one provided by spotify.

## search_and_get_best_match function

[PUR.] To return the best possible match for a given song from spotify

[REA.] To cater to the most common use case where you only need the best possible YouTube
Music match link

<br><br>

# utils

## search_for_song function

[PUR.] Get song  details from a search query instead of from a URL

[REA.] The end-user might not always attempt to download songs from their URL's. To
always use URL's would be a cumbersome process. This bypasses that effort by fetching the
URL from a given query.

## get_album_tracks

[PUR.] Get details of all tracks in an album

[REA.] Having to individually list out each track in an album is a pain 

## get_playlist_tracks

[PUR.] Get details of all tracks in a playlist

[REA.] Having to individually list out each track in a playlist is a greater pain than
listing out each track in an album.

# downloads

## downloadManager class

[PUR.] To download given songs, singly or in parallel, convert them to MP3 and embed
required metadata

[REA.] Come on, the whole point of spotDL is to download stuff

## downloadTracker class

[PUR.] to track the progress of downloads and enable download resuming

[REA]. considering that downloading takes place in parallel, it is much easier to have
tracking of downloads progressing live-time in parallel to downloading in a separate
process instead of having it tracked in the main python process (its much simpler too)

## displayManager class

[PUR.] To ensure a clean UI for users even when downloading stuff in parallel

[REA.] Using print methods in parallel with carriage returns (\r) for clean updates
will print in new lines as the print call is from different processes. THis creates
a need for a common point of output. The easiest hi-lv way to do that is an autoproxy.