from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import SpotifyClient
import spotdl.search.audioProvider as audioProvider
import spotdl.search.metadataProvider as metadataProvider

from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
import argparse

# =======================
# === Master Gatherer ===
# =======================


def from_query(request: str, output_format: str = None):
    songObjList = []
    if "open.spotify.com" in request and "track" in request:
        print("Fetching Song...")
        songObjList = [songobj_from_spotify_url(request, output_format)]

    elif "open.spotify.com" in request and "album" in request:
        print("Fetching Album...")
        songObjList = get_album_tracks(request, output_format)

    elif "open.spotify.com" in request and "playlist" in request:
        print("Fetching Playlist...")
        songObjList = get_playlist_tracks(request, output_format)

    elif "open.spotify.com" in request and "artist" in request:
        print("Fetching artist...")
        songObjList = get_artist_tracks(request, output_format)

    elif request == "saved":
        print("Fetching Saved Songs...")
        songObjList = get_saved_tracks(output_format)

    else:
        print('Searching Spotify for song named "%s"...' % request)
        try:
            songObjList = from_search_term(request, output_format)
        except Exception as e:
            print(e)

    # filter out NONE songObj items (already downloaded)
    songObjList = [songObj for songObj in songObjList if songObj]

    return songObjList


# All other functions in this file call this one


def songobj_from_spotify_url(spotifyURL: str, output_format: str = None):
    # check if URL is a playlist, user, artist or album, if yes raise an Exception,
    # else procede

    # Get the Song Metadata
    print(f"Gathering Spotify Metadata for: {spotifyURL}")
    rawTrackMeta, rawArtistMeta, rawAlbumMeta = metadataProvider.from_url(spotifyURL)

    songName = rawTrackMeta["name"]
    albumName = rawTrackMeta["album"]["name"]
    contributingArtists = []
    for artist in rawTrackMeta["artists"]:
        contributingArtists.append(artist["name"])
    duration = round(rawTrackMeta["duration_ms"] / 1000, ndigits=3)

    convertedFileName = SongObj.create_file_name(
        songName, [artist["name"] for artist in rawTrackMeta["artists"]]
    )

    if output_format is None:
        output_format = "mp3"

    convertedFilePath = Path(".", f"{convertedFileName}.{output_format}")
    displayName = ", ".join(contributingArtists) + " - " + songName

    # if a song is already downloaded skip it
    if convertedFilePath.is_file():
        print(f'Skipping "{convertedFileName}" as it\'s already downloaded')
        return None

    # Get the song's downloadable audio link
    print(f'Searching YouTube for "{displayName}"', end="\r")
    youtubeLink = audioProvider.search_and_get_best_match(
        songName, contributingArtists, albumName, duration
    )
    if youtubeLink is None:
        # raise Exception("Could not match any of the results on YouTube")
        print("Could not match any of the results on YouTube. Skipping")
        return None
    else:
        print(" " * (len(displayName) + 25), end="\r")
        print(f'Found YouTube URL for "{displayName}" : {youtubeLink}')

    # (try to) Get lyrics from Genius
    try:
        lyrics = metadataProvider.get_song_lyrics(songName, contributingArtists)
    except (AttributeError, IndexError):
        lyrics = ""

    return SongObj(rawTrackMeta, rawAlbumMeta, rawArtistMeta, youtubeLink, lyrics)


# =======================
# === Other Gatherers ===
# =======================


def from_dump(dataDump: dict):
    rawTrackMeta = dataDump["rawTrackMeta"]
    rawAlbumMeta = dataDump["rawAlbumMeta"]
    rawArtistMeta = dataDump["rawAlbumMeta"]
    youtubeLink = dataDump["youtubeLink"]
    lyrics = dataDump["lyrics"]

    return SongObj(rawTrackMeta, rawAlbumMeta, rawArtistMeta, youtubeLink, lyrics)


def from_search_term(query: str, output_format: str = None) -> List[SongObj]:
    """
    `str` `query` : what you'd type into Spotify's search box
    Queries Spotify for a song and returns the best match
    """

    # get a spotify client
    spotifyClient = SpotifyClient()

    tracks = []

    # get possible matches from spotify
    result = spotifyClient.search(query, type="track")

    # return first result link or if no matches are found, raise and Exception
    if len(result["tracks"]["items"]) == 0:
        raise Exception("No song matches found on Spotify")
    else:
        songUrl = "http://open.spotify.com/track/" + result["tracks"]["items"][0]["id"]
        song = songobj_from_spotify_url(songUrl, output_format)
        tracks.append(song)

    return tracks


def get_album_tracks(albumUrl: str, output_format: str = None) -> List[SongObj]:
    """
    `str` `albumUrl` : Spotify Url of the album whose tracks are to be
    retrieved
    returns a `list<songObj>` containing Url's of each track in the given album
    """

    spotifyClient = SpotifyClient()
    albumTracks = []

    trackResponse = spotifyClient.album_tracks(albumUrl)

    # while loop acts like do-while
    while True:

        for track in trackResponse["items"]:
            song = songobj_from_spotify_url(
                "https://open.spotify.com/track/" + track["id"], output_format
            )

            if song is not None and song.get_youtube_link() is not None:
                albumTracks.append(song)

        # check if more tracks are to be passed
        if trackResponse["next"]:
            trackResponse = spotifyClient.album_tracks(
                albumUrl, offset=len(albumTracks)
            )
        else:
            break

    return albumTracks


def get_artist_tracks(artistUrl: str, output_format: str = None) -> List[SongObj]:
    """
    `str` `albumUrl` : Spotify Url of the artist whose tracks are to be
    retrieved
    returns a `list<songObj>` containing Url's of each track in the artist profile
    """

    spotifyClient = SpotifyClient()
    albums = []
    albumTracks: Dict[str, SongObj] = {}
    offset = 0

    artistResponse = spotifyClient.artist_albums(artistUrl)

    # loop until we get all tracks from all albums/playlists
    while True:
        for album in artistResponse["items"]:

            # return an iterable containing the string's alphanumeric characters
            alphaNumericFilter = filter(str.isalnum, album["name"].lower())

            # join all characters into one string
            albumName = "".join(alphaNumericFilter)

            # check if we've already downloaded album with this name
            if not (albumName in albums) and not (
                # exclude compilation playlists
                album["album_group"] == "appears_on"
                and album["album_type"] in ["compilation"]
            ):
                trackResponse = spotifyClient.album_tracks(album["uri"])

                # loop until we get all tracks from playlist
                while True:
                    for track in trackResponse["items"]:
                        # return an iterable containing the string's alphanumeric characters
                        alphaNumericFilter = filter(str.isalnum, track["name"].lower())

                        # join all characters into one string
                        trackName = "".join(alphaNumericFilter)

                        # check if we've alredy downloaded this track
                        if albumTracks.get(trackName) is None:
                            for artist in track["artists"]:
                                # get artist id from url
                                # https://api.spotify.com/v1/artists/1fZAAHNWdSM5gqbi9o5iEA/albums
                                # split string
                                # ['https:', '', 'api.spotify.com',
                                # 'v1', 'artists', '1fZAAHNWdSM5gqbi9o5iEA', 'albums']
                                # get second element from the end
                                # '1fZAAHNWdSM5gqbi9o5iEA'
                                artistId = artistResponse["href"].split("/")[-2]

                                # ignore tracks that are not from our artist by checking
                                # the id
                                if artist["id"] == artistId:
                                    song = songobj_from_spotify_url(
                                        "https://open.spotify.com/track/" + track["id"],
                                        output_format,
                                    )

                                    if (
                                        song is not None
                                        and song.get_youtube_link() is not None
                                    ):
                                        albumTracks[trackName] = song

                    # check if more tracks are to be passed
                    if trackResponse["next"]:
                        trackResponse = spotifyClient.album_tracks(
                            album["uri"], offset=len(albumTracks)
                        )
                    else:
                        break

                albums.append(albumName)

        offset += len(artistResponse["items"])

        # check if more albums are to be passed
        if artistResponse["next"]:
            artistResponse = spotifyClient.artist_albums(artistUrl, offset=offset)
        else:
            break

    return list(albumTracks.values())


def get_playlist_tracks(playlistUrl: str, output_format: str = None) -> List[SongObj]:
    """
    `str` `playlistUrl` : Spotify Url of the album whose tracks are to be
    retrieved
    returns a `list<songObj>` containing Url's of each track in the given playlist
    """

    spotifyClient = SpotifyClient()
    playlistTracks = []

    playlistResponse = spotifyClient.playlist_tracks(playlistUrl)

    # while loop to mimic do-while
    while True:

        for songEntry in playlistResponse["items"]:
            if songEntry["track"] is None or songEntry["track"]["id"] is None:
                continue

            song = songobj_from_spotify_url(
                "https://open.spotify.com/track/" + songEntry["track"]["id"],
                output_format,
            )

            if song is not None and song.get_youtube_link() is not None:
                playlistTracks.append(song)

        # check if more tracks are to be passed
        if playlistResponse["next"]:
            playlistResponse = spotifyClient.playlist_tracks(
                playlistUrl,
                offset=playlistResponse["offset"] + playlistResponse["limit"],
            )
        else:
            break

    return playlistTracks


def get_saved_tracks(output_format: str = None) -> List[SongObj]:
    """
    returns a `list<songObj>` containing Url's of each track in the user's saved tracks
    """

    spotifyClient = SpotifyClient()

    savedTracks = []

    savedTracksResponse = spotifyClient.current_user_saved_tracks()

    while True:
        for songEntry in savedTracksResponse["items"]:
            if songEntry["track"] is None or songEntry["track"]["id"] is None:
                continue

            song = songobj_from_spotify_url(
                "https://open.spotify.com/track/" + songEntry["track"]["id"],
                output_format,
            )

            if song is not None and song.get_youtube_link() is not None:
                savedTracks.append(song)

        # check if more tracks are to be passed
        if savedTracksResponse["next"]:
            savedTracksResponse = spotifyClient.current_user_saved_tracks(
                offset=savedTracksResponse["offset"] + savedTracksResponse["limit"]
            )
        else:
            break

    return savedTracks
