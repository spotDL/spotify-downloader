# What is this file?

This file contains a working specification of all interfaces used in this
project. As it is still in dev, the interfaces declared here are likely to
change often and without warning.

# Index

- [Music Search Interface](#01.-Music-Search-Interface)
- [Metadata Search Interface](#02.-Metadata-Search-Interface)
- [Metadata Object Interface](#03.-Metadata-Object-Interface)
- [Song Object Interface](#04.-Song-Object-Interface)
- [Downloads Interface](#05.-Downloads-Interface)

# Interfaces

## 01. Music Search Interface

Functions defined here:
- [searchFromUrl](#searchFromUrl)
- [searchAllFromUrl](#searchAllFromUrl)
- [searchFromName](#searchFromName)
- [searchAllFromName](#searchAllFromName)

### searchFromUrl

| Parameter | Type | Description |
| --- | --- | --- |
| spotifyUrl | str | The spotify Url of a song |
| **RETURN** | [song](#04.-Song-Object-Interface) | The details of the ***best*** match |

<br><br>

### searchAllFromUrl

| Parameter | Type | Description |
| --- | --- | --- |
| spotifyUrl | str | The spotify Url of a song |
| **RETURN** | list\<song> | List of all matches |

<br><br>

### searchFromName

| Parameter | Type | Description |
| --- | --- | --- |
| songName | str | name of the song |
| artist (optional) | str | name of the artist, defaults to `None` |
| **RETURN** | [song](#04.-Song-Object-Interface) | The details of the ***best*** match |

<br><br>

### searchAllFromName

| Parameter | Type | Description |
| --- | --- | --- |
| songName | str | name of the song |
| artist (optional) | str | name of the artist, defaults to `None` |
| **RETURN** | list\<song> | List of all matches |

<br><br>

<br><br>

## 02. Metadata Search Interface

Functions defined here:
- [getDetails](#getDetails)
- [getLyrics](#getLyrics)

### getDetails

| Parameter | Type | Description |
| --- | --- | --- |
| song | [song](#04.-Song-Object-Interface) | song object of the required song |
| **RETURN** | [metadata](#03.-Metadata-Object-Interface)| The ***best*** match |

<br><br>

### getLyrics

| Parameter | Type | Description |
| --- | --- | --- |
| song | [song](#04.-Song-Object-Interface) | song object of the required song |
| **RETURN** | str | lyrics of the song, None if not available |

<br><br>

## 03. Metadata Object Interface

Functions defined here:
- [getSongName](#getSongName)
- [getTrackNumber](#getTrackNumber)
- [getLength](#getLength)
- [getContributingArtists](#getContributingArtists)
- [getAlbumName](#getAlbumName)
- [getAlbumArtists](#getAlbumArtists)
- [getAlbumRelease](#getAlbumRelease)
- [getAlbumArtUrl](#getAlbumArtUrl)
- [getLyrics](#getLyrics)
- [getDataDump](#getDataDump)

### getSongName

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | Name of the song (not artist - song, just song name) |

<br><br>

### getTrackNumber

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | int | Track number within the album |

<br><br>

### getLength

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | int | Length of song in seconds |

<br><br>

### getContributingArtists

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | list\<str> | Names of all artists in the song |

<br><br>

### getAlbumName

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | Name of the album from which the song comes |

<br><br>

### getAlbumArtists

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | list\<str> | Names of all involved artists |

<br><br>

### getAlbumRelease

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | year/date of album release formatted yyy-mm-dd |

<br><br>

### getAlbumArtUrl

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | Url for album art image |

<br><br>

### getLyrics

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | un-time-synched lyrics |

<br><br>

### getDataDump

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | any | Returns all the gathered metadata, None if absent |

Note, The return value of the `getDataDump()` function can be of any kind -
dicts, lists, JSON responses, custom objects, or even complex dict-list nested
structures, freedom to the author. We encourage the authors of an
implementation of the interface to also document the return format/type of
the `getDataDump` function.

<br><br>

## 04. Song Object Interface

Functions defined here:
- [getSongName](#getSongName)
- [getContributingArtists](#getContributingArtists)
- [getSpotifyLength](#getSpotifyLength)
- [getYoutubeLength](#getYoutubeLength)
- [getSpotifyLink](#getSpotifyLink)
- [getYoutubeLink](#getYoutubeLink)
- [getMetaData](#getMetaData)

### getSongName

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | Song's name |

<br><br>

### getContributingArtists

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | list\<str> | List of involved artists |

Note, List of artists need not be complete but at least one artist name is
required.

<br><br>

### getSpotifyLength

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | int | length of song in seconds according to spotify |

<br><br>

### getYoutubeLength

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | int | length of song in seconds according to YouTube |

<br><br>

### getSpotifyLink

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | Link to listen to song on Spotify |

<br><br>

### getYoutubeLink

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | str | Link to listen to song on YouTube |

<br><br>

### getMetaData

| Parameter | Type | Description |
| --- | --- | --- |
| **RETURN** | [metadata](#03.-Metadata-Object-Interface) | Metadata of the given song |

<br><br>

Note, I realize that there might seem to be sizeable overlap b/w the Song
Object and Metadata Object Interfaces, Their purposes are fundamentally
different hence they are separate. The Song Object Interface aims to
identify any song uniquely. The Metadata Object Interface aims to provide
basic details to be embedded into a .mp3 file so that music managers
(Groove Music, VLC, WMP, etc...) can effectively catalog them along with a
little extra details (like lyrics).

## 05. Downloads Interface

Functions Defined here:
- [download](#download)

### download

Function: Download song, converts format, applies metadata

| Parameter | Type | Description |
| --- | --- | --- |
| song | [song](#04.-Song-Object-Interface) | the song to download |
| metadata | [metadata](#03.-Metadata-Object-Interface) | metadata of song to download |
| format | str | format to save the downloaded song, defaults to '.mp3' |
| **RETURN** | None | - |
