<!--- mdformat-toc start --slug=github --->

# PURPOSES

## What is this document?

v3.0.0 of spotDL was found to be lacking in many ways. While it fixed many of the issues
its predecessor had, it brought with it, many issues of its own. Primarily, poor
access-control and unnecessary functionality.

To address the issues of mucked-up class's, functions, modules and unnecessary
functionality this project here on works on zero-base-accounting - if you can't justify
it's need, you don't build it. The purpose of various functions, modules and classes will
be listed here and adhered to strictly. This document then, represents the primary source
of truth as to the requirement and responsibility of each unit of code.

## Structure

- module name
  - class or function name
    - **PURPOSE** and **REASON**

Purpose and Reason are fairly similar words. By purpose we mean just what that class or
function is meant to do, it's functionality. By Reason we mean justification as to why
that class/function should exist

______________________________________________________________________

## songObj

### songObj class

**PURPOSE** songObj is meant to serve dual purposes - to act as an ***exchange currency***
through out spotDL and as a central repository of all known details of a given song.

**REASON** A lot of what spotDL does requires passing around of various details about
songs. The songObj serves as a ***single-point-of-access*** to all the various details we
might seek. The eliminates the need to query the same info multiple times from a server
while eliminating any ambiguity as to code unit return types. It also allows a consistent
interface to song details thereby adding to simplicity.

______________________________________________________________________

## spotifyClient

### get_spotify_client function

**PURPOSE** ensure that only a single instance of spotifyClient exists throughout the
codebase.

**REASON** Having different parts of code having to initialize spotifyClients when
required, would make for a lot of duplicate code. Serves as a ***single-point-of-access***
to a ***singleton spotifyClient***.

**SEE ALSO** [initialize](#initialize-function)

### initialize function

**PURPOSE** To create a cache a SpotifyClient

**REASON** Clubbing of client creation/caching with singleton-access requires passing of a
client_id & client_secret the first time but not for subsequent calls. This ambiguity as
to passing args is avoided.

______________________________________________________________________

## provider

### \_\_query_and_simplify function

**PURPOSE** To query YouTube Music and extract details from their hopelessly nested
responses

**REASON** Compartmentalize YouTube link matching. The whole search providing interface
can be jointed into one massive function but then, making changes would be unduly
difficult.

### search_and_order function

**PURPOSE** To filter, and measure the likelihood of available YouTube Music results being
the songs the user is after

**REASON** Although YouTube Music's results are far better than YouTube's, it still relies
on an extent upon the user to select the best match according to what ever he/she/them is
searching for. A program can not identify the best match like a human being who would
identify the song by video thumbnail or album art. So we attempt to measure the extent to
which it is the same song as the one provided by spotify.

### search_and_get_best_match function

**PURPOSE** To return the best possible match for a given song from spotify

**REASON** To cater to the most common use case where you only need the best possible
YouTube Music match link

______________________________________________________________________

## utils

### search_for_song function

**PURPOSE** Get song details from a search query instead of from a URL

**REASON** The end-user might not always attempt to download songs from their URL's. To
always use URL's would be a cumbersome process. This bypasses that effort by fetching the
URL from a given query.

### get_album_tracks

**PURPOSE** Get details of all tracks in an album

**REASON** Having to individually list out each track in an album is a pain

### get_playlist_tracks

**PURPOSE** Get details of all tracks in a playlist

**REASON** Having to individually list out each track in a playlist is a greater pain than
listing out each track in an album.

## downloads

### downloadManager class

**PURPOSE** To download given songs, singly or in parallel, convert them to MP3 and embed
required metadata

**REASON** Come on, the whole point of spotDL is to download stuff

### downloadTracker class

**PURPOSE** to track the progress of downloads and enable download resuming

**REASON** considering that downloading takes place in parallel, it is much easier to have
tracking of downloads progressing live-time in parallel to downloading in a separate
process instead of having it tracked in the main python process (its much simpler too)

### displayManager class

**PURPOSE** To ensure a clean UI for users even when downloading stuff in parallel

**REASON** Using print methods in parallel with carriage returns (\\r) for clean updates
will print in new lines as the print call is from different processes. THis creates a need
for a common point of output. The easiest hi-lv way to do that is an autoproxy.
