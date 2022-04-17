from spotdl.search import SpotifyClient


def from_url(spotify_url: str):
    if "open.spotify.com" not in spotify_url or "track" not in spotify_url:
        raise Exception(f"passed URL is not that of a track: {spotify_url}")

    # query spotify for song, artist, album details
    spotify_client = SpotifyClient()

    raw_track_meta = spotify_client.track(spotify_url)

    if raw_track_meta is None:
        raise Exception(
            "Couldn't get metadata, check if you have passed correct track id"
        )

    try:
        primary_artist_id = raw_track_meta["artists"][0]["id"]
        raw_artist_meta = spotify_client.artist(primary_artist_id)
    except:
        raw_artist_meta = ""

    try:
        albumId = raw_track_meta["album"]["id"]
        raw_album_meta = spotify_client.album(albumId)
    except:
        raw_album_meta = ""

    return raw_track_meta, raw_artist_meta, raw_album_meta
