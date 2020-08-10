# What is this file?

This file contains a working specification of all interfaces used in this
project. As it is still in dev, the interfaces declared here are likely to
change often and without warning.

# Index

- [Music Search Interface](#01.%20Music%20Search%20Interface)
- [Metadata Search Interface](#02.%20Metadata%20Search%20Interface)

# Interfaces

## 01. Music Search Interface

Functions defined here:
- [searchFromLink](#searchFromLink)
- [searchAllFromLink](#searchAllFromLink)
- [searchFromName](#searchFromName)
- [searchAllFromName](#searchAllFromName)

### searchFromLink

| Parameter | Type | Description |
| --- | --- | --- |
| link | str | The spotify URI of a song |
| **RETURN** | [song](objects.md#Song) | The details of the ***best*** match |

<br><br>

### searchAllFromLink

| Parameter | Type | Description |
| --- | --- | --- |
| link | str | The spotify URI of a song |
| **RETURN** | list | List of all matches as [song](objects.md#Song) objects |

<br><br>

### searchFromName

| Parameter | Type | Description |
| --- | --- | --- |
| songName | str | name of the song |
| artist (optional) | str | name of the artist, defaults to `None` |
| **RETURN** | [song](objects.md#Song) | The details of the ***best*** match |

<br><br>

### searchAllFromName

| Parameter | Type | Description |
| --- | --- | --- |
| songName | str | name of the song |
| artist (optional) | str | name of the artist, defaults to `None` |
| **RETURN** | list | List of all matches as [song](objects.md#Song) objects |

<br><br>

## 02. Metadata Search Interface

Functions defined here:
- [getDetails](#getDetails)
- [getLyrics](#getLyrics)

### getDetails

| Parameter | Type | Description |
| --- | --- | --- |
| song | [song](objects.md#Song) | song object of the required song |
| **RETURN** | [metadata](objects.md#Metadata)| The ***best*** match |

<br><br>

### getLyrics

| Parameter | Type | Description |
| --- | --- | --- |
| song | [song](objects.md#Song) | song object of the required song |
| **RETURN** | str | lyrics of the song |

<br><br>

## Go [back](workingDocs.md#Search%20Providers) to where you left off