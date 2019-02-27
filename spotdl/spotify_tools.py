import spotipy
import spotipy.oauth2 as oauth2
import lyricwikia

from slugify import slugify
from titlecase import titlecase
from logzero import logger as log
import pprint
import sys
import os
import functools

from spotdl import const
from spotdl import internals

spotify = None


def generate_token():
    """ Generate the token. """
    credentials = oauth2.SpotifyClientCredentials(
        client_id=const.args.spotify_client_id,
        client_secret=const.args.spotify_client_secret,
    )
    token = credentials.get_access_token()
    return token


def must_be_authorized(func, spotify=spotify):
    def wrapper(*args, **kwargs):
        global spotify
        try:
            assert spotify
            return func(*args, **kwargs)
        except (AssertionError, spotipy.client.SpotifyException):
            token = generate_token()
            spotify = spotipy.Spotify(auth=token)
            return func(*args, **kwargs)
    return wrapper


@must_be_authorized
def generate_metadata(raw_song):
    """ Fetch a song's metadata from Spotify. """
    if internals.is_spotify(raw_song):
        # fetch track information directly if it is spotify link
        log.debug("Fetching metadata for given track URL")
        meta_tags = spotify.track(raw_song)
    else:
        # otherwise search on spotify and fetch information from first result
        log.debug('Searching for "{}" on Spotify'.format(raw_song))
        try:
            meta_tags = spotify.search(raw_song, limit=1)["tracks"]["items"][0]
        except IndexError:
            return None
    artist = spotify.artist(meta_tags["artists"][0]["id"])
    album = spotify.album(meta_tags["album"]["id"])

    try:
        meta_tags[u"genre"] = titlecase(artist["genres"][0])
    except IndexError:
        meta_tags[u"genre"] = None
    try:
        meta_tags[u"copyright"] = album["copyrights"][0]["text"]
    except IndexError:
        meta_tags[u"copyright"] = None
    try:
        meta_tags[u"external_ids"][u"isrc"]
    except KeyError:
        meta_tags[u"external_ids"][u"isrc"] = None

    meta_tags[u"release_date"] = album["release_date"]
    meta_tags[u"publisher"] = album["label"]
    meta_tags[u"total_tracks"] = album["tracks"]["total"]

    log.debug("Fetching lyrics")

    try:
        meta_tags["lyrics"] = lyricwikia.get_lyrics(
            meta_tags["artists"][0]["name"], meta_tags["name"]
        )
    except lyricwikia.LyricsNotFound:
        meta_tags["lyrics"] = None

    # Some sugar
    meta_tags["year"], *_ = meta_tags["release_date"].split("-")
    meta_tags["duration"] = meta_tags["duration_ms"] / 1000.0
    meta_tags["spotify_metadata"] = True
    # Remove unwanted parameters
    del meta_tags["duration_ms"]
    del meta_tags["available_markets"]
    del meta_tags["album"]["available_markets"]

    log.debug(pprint.pformat(meta_tags))
    return meta_tags


@must_be_authorized
def write_user_playlist(username, text_file=None):
    """ Write user playlists to text_file """
    links = get_playlists(username=username)
    playlist = internals.input_link(links)
    return write_playlist(playlist, text_file)


@must_be_authorized
def get_playlists(username):
    """ Fetch user playlists when using the -u option. """
    playlists = spotify.user_playlists(username)
    links = []
    check = 1

    while True:
        for playlist in playlists["items"]:
            # in rare cases, playlists may not be found, so playlists['next']
            # is None. Skip these. Also see Issue #91.
            if playlist["name"] is not None:
                log.info(
                    u"{0:>5}. {1:<30}  ({2} tracks)".format(
                        check, playlist["name"], playlist["tracks"]["total"]
                    )
                )
                playlist_url = playlist["external_urls"]["spotify"]
                log.debug(playlist_url)
                links.append(playlist_url)
                check += 1
        if playlists["next"]:
            playlists = spotify.next(playlists)
        else:
            break

    return links


@must_be_authorized
def fetch_playlist(playlist):
    try:
        playlist_id = internals.extract_spotify_id(playlist)
    except IndexError:
        # Wrong format, in either case
        log.error("The provided playlist URL is not in a recognized format!")
        sys.exit(10)
    try:
        results = spotify.user_playlist(
            user=None, playlist_id=playlist_id, fields="tracks,next,name"
        )
    except spotipy.client.SpotifyException:
        log.error("Unable to find playlist")
        log.info("Make sure the playlist is set to publicly visible and then try again")
        sys.exit(11)

    return results


@must_be_authorized
def write_playlist(playlist_url, text_file=None):
    playlist = fetch_playlist(playlist_url)
    tracks = playlist["tracks"]
    if not text_file:
        text_file = u"{0}.txt".format(slugify(playlist["name"], ok="-_()[]{}"))
    return write_tracks(tracks, text_file)


@must_be_authorized
def fetch_album(album):
    album_id = internals.extract_spotify_id(album)
    album = spotify.album(album_id)
    return album


@must_be_authorized
def fetch_albums_from_artist(artist_url, album_type=None):
    """
    This funcction returns all the albums from a give artist_url using the US
    market
    :param artist_url - spotify artist url
    :param album_type - the type of album to fetch (ex: single) the default is
                        all albums
    :param return - the album from the artist
    """

    # fetching artist's albums limitting the results to the US to avoid duplicate
    # albums from multiple markets
    artist_id = internals.extract_spotify_id(artist_url)
    results = spotify.artist_albums(artist_id, album_type=album_type, country="US")

    albums = results["items"]

    # indexing all pages of results
    while results["next"]:
        results = spotify.next(results)
        albums.extend(results["items"])

    return albums


@must_be_authorized
def write_all_albums_from_artist(artist_url, text_file=None):
    """
    This function gets all albums from an artist and writes it to a file in the
    current working directory called [ARTIST].txt, where [ARTIST] is the artist
    of the album
    :param artist_url - spotify artist url
    :param text_file - file to write albums to
    """

    album_base_url = "https://open.spotify.com/album/"

    # fetching all default albums
    albums = fetch_albums_from_artist(artist_url, album_type=None)

    # if no file if given, the default save file is in the current working
    # directory with the name of the artist
    if text_file is None:
        text_file = albums[0]["artists"][0]["name"] + ".txt"

    for album in albums:
        # logging album name
        log.info("Fetching album: " + album["name"])
        write_album(album_base_url + album["id"], text_file=text_file)


@must_be_authorized
def write_album(album_url, text_file=None):
    album = fetch_album(album_url)
    tracks = spotify.album_tracks(album["id"])
    if not text_file:
        text_file = u"{0}.txt".format(slugify(album["name"], ok="-_()[]{}"))
    return write_tracks(tracks, text_file)


@must_be_authorized
def write_tracks(tracks, text_file):
    log.info(u"Writing {0} tracks to {1}".format(tracks["total"], text_file))
    track_urls = []
    with open(text_file, "a") as file_out:
        while True:
            for item in tracks["items"]:
                if "track" in item:
                    track = item["track"]
                else:
                    track = item
                try:
                    track_url = track["external_urls"]["spotify"]
                    log.debug(track_url)
                    file_out.write(track_url + "\n")
                    track_urls.append(track_url)
                except KeyError:
                    log.warning(
                        u"Skipping track {0} by {1} (local only?)".format(
                            track["name"], track["artists"][0]["name"]
                        )
                    )
            # 1 page = 50 results
            # check if there are more pages
            if tracks["next"]:
                tracks = spotify.next(tracks)
            else:
                break
    return track_urls
