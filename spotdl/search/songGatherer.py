from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import SpotifyClient
import spotdl.search.audioProvider as audioProvider
import spotdl.search.metadataProvider as metadataProvider

from typing import List


# =======================
# === Master Gatherer ===
# =======================

def from_query(request: str):
    if "open.spotify.com" in request and "track" in request:
        print("Fetching Song...")
        songObjList = songobj_from_spotify_url(request)

    elif "open.spotify.com" in request and "album" in request:
        print("Fetching Album...")
        songObjList = get_album_tracks(request)

    elif "open.spotify.com" in request and "playlist" in request:
        print("Fetching Playlist...")
        songObjList = get_playlist_tracks(request)

    elif "open.spotify.com" in request and "artist" in request:
        print("Fetching artist...")
        songObjList = get_artist_tracks(request)

    else:
        print('Searching Spotify for song named "%s"...' % request)
        try:
            songObjList = from_search_term(request)
        except Exception as e:
            print(e)

    return songObjList



# All other functions in this file call this one

def songobj_from_spotify_url(spotifyURL: str):
    # check if URL is a playlist, user, artist or album, if yes raise an Exception,
    # else procede

    # Get the Song Metadata
    print(f"Gathering Spotify Metadata for: {spotifyURL}")
    rawTrackMeta, rawArtistMeta, rawAlbumMeta = metadataProvider.from_url(
        spotifyURL
    )

    songName = rawTrackMeta["name"]
    albumName = rawTrackMeta["album"]["name"]
    contributingArtists = []
    for artist in rawTrackMeta["artists"]:
        contributingArtists.append(artist["name"])
    duration = round(rawTrackMeta["duration_ms"] / 1000, ndigits=3)

    # Get the song's downloadable audio link
    print(f"Searching YouTube for \"" + ", ".join(contributingArtists) + " - " + songName + "\"")
    youtubeLink = audioProvider.search_and_get_best_match(
        songName, contributingArtists, albumName, duration
    )
    print(f"Found:", youtubeLink)

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



def from_search_term(query: str) -> SongObj:
    """
    `str` `query` : what you'd type into spotify's search box
    Queries Spotify for a song and returns the best match
    """

    # get a spotify client
    spotifyClient = SpotifyClient()

    # get possible matches from spotify
    result = spotifyClient.search(query, type="track")

    # return first result link or if no matches are found, raise and Exception
    if len(result["tracks"]["items"]) == 0:
        raise Exception("No song matches found on Spotify")
    else:
        for songResult in result["tracks"]["items"]:
            songUrl = "http://open.spotify.com/track/" + songResult["id"]
            song = songobj_from_spotify_url(songUrl)

            if song.get_youtube_link() is not None:
                return song

        raise Exception("Could not match any of the results on YouTube")


def get_album_tracks(albumUrl: str) -> List[SongObj]:
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
            song = songobj_from_spotify_url("https://open.spotify.com/track/" + track["id"])

            if song.get_youtube_link() is not None:
                albumTracks.append(song)

        # check if more tracks are to be passed
        if trackResponse["next"]:
            trackResponse = spotifyClient.album_tracks(
                albumUrl, offset=len(albumTracks)
            )
        else:
            break

    return albumTracks


def get_artist_tracks(artistUrl: str) -> List[SongObj]:
    """
    `str` `albumUrl` : Spotify Url of the artist whose tracks are to be
    retrieved
    returns a `list<songObj>` containing Url's of each track in the artist profile
    """

    spotifyClient = SpotifyClient()
    artistTracks = []
    offset = 0

    artistResponse = spotifyClient.artist_albums(artistUrl)

    # while loop acts like do-while
    while True:
        for album in artistResponse["items"]:
            # get albums and singles
            if not (
                (album["album_group"] == "appears_on")
                and (album["album_type"] in ["album", "compilation"])
            ):
                artistTracks.extend(get_album_tracks(album["id"]))
            # get features from other artists albums
            elif (
                album["album_group"] == "appears_on" and album["album_type"] == "album"
            ):
                trackResponse = spotifyClient.album_tracks(album["uri"])
                albumTracks = []

                # while loop acts like do-while
                while True:
                    for track in trackResponse["items"]:
                        for artist in track["artists"]:
                            if artist["id"] == artistResponse["href"].split("/")[-2]:
                                song = songobj_from_spotify_url(
                                    "https://open.spotify.com/track/" + track["id"]
                                )

                                if song.get_youtube_link() is not None:
                                    albumTracks.append(song)

                    # check if more tracks are to be passed
                    if trackResponse["next"]:
                        trackResponse = spotifyClient.album_tracks(
                            album["uri"], offset=len(albumTracks)
                        )
                    else:
                        break

                artistTracks.extend(albumTracks)

        offset += len(artistResponse["items"])

        # check if more albums are to be passed
        if artistResponse["next"]:
            artistResponse = spotifyClient.artist_albums(artistUrl, offset=offset)
        else:
            break

    return artistTracks


def get_playlist_tracks(playlistUrl: str) -> List[SongObj]:
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
                "https://open.spotify.com/track/" + songEntry["track"]["id"]
            )

            if song.get_youtube_link() is not None:
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
