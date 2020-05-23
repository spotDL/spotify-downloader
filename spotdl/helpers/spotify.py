from spotdl.authorize.services import AuthorizeSpotify
import spotdl.util

import sys
import spotipy

import logging
logger = logging.getLogger(__name__)

try:
    from slugify import SLUG_OK, slugify
except ImportError:
    logger.error("Oops! `unicode-slugify` was not found.")
    logger.info("Please remove any other slugify library and install `unicode-slugify`.")
    raise


class SpotifyHelpers:
    def __init__(self, spotify=None):
        if spotify is None:
            spotify = AuthorizeSpotify()
        self.spotify = spotify

    def prompt_for_user_playlist(self, username):
        """ Write user playlists to target_file """
        playlists = self.fetch_user_playlist_urls(username)
        for i, playlist in enumerate(playlists, 1):
            playlist_details = "{0}. {1:<30}  ({2} tracks)".format(
                i, playlist["name"], playlist["tracks"]["total"]
            )
            print(playlist_details, file=sys.stderr)
        print("", file=sys.stderr)
        playlist = spotdl.util.prompt_user_for_selection(playlists)
        return playlist["external_urls"]["spotify"]

    def fetch_user_playlist_urls(self, username):
        """ Fetch user playlists when using the -u option. """
        logger.debug('Fetching playlists for "{username}".'.format(username=username))
        playlists = self.spotify.user_playlists(username)
        collected_playlists = []
        check = 1

        while True:
            for playlist in playlists["items"]:
                # in rare cases, playlists may not be found, so playlists['next']
                # is None. Skip these. Also see Issue #91.
                if playlist["name"] is not None:
                    collected_playlists.append(playlist)
                    check += 1
            if playlists["next"]:
                playlists = self.spotify.next(playlists)
            else:
                break

        return collected_playlists

    def fetch_playlist(self, playlist_url):
        logger.debug('Fetching playlist "{playlist}".'.format(playlist=playlist_url))
        try:
            results = self.spotify.playlist(playlist_url, fields="tracks,next,name")
        except spotipy.client.SpotifyException:
            logger.exception(
                "Unable to find playlist. Make sure the playlist is set "
                "to publicly visible and then try again."
            )

        return results

    def write_playlist_tracks(self, playlist, target_file=None):
        tracks = playlist["tracks"]
        if not target_file:
            target_file = u"{0}.txt".format(slugify(playlist["name"], ok="-_()[]{}"))
        return self.write_tracks(tracks, target_file)

    def fetch_album(self, album_uri):
        logger.debug('Fetching album "{album}".'.format(album=album_uri))
        album = self.spotify.album(album_uri)
        return album

    def write_album_tracks(self, album, target_file=None):
        tracks = self.spotify.album_tracks(album["id"])
        if not target_file:
            target_file = u"{0}.txt".format(slugify(album["name"], ok="-_()[]{}"))
        return self.write_tracks(tracks, target_file)

    def fetch_albums_from_artist(self, artist_uri, album_type=None):
        """
        This function returns all the albums from a give artist_uri using the US
        market
        :param artist_uri - spotify artist uri
        :param album_type - the type of album to fetch (ex: single) the default is
                            all albums
        :param return - the album from the artist
        """

        logger.debug('Fetching all albums for "{artist}".'.format(artist=artist_uri))
        # fetching artist's albums limitting the results to the US to avoid duplicate
        # albums from multiple markets
        results = self.spotify.artist_albums(artist_uri, album_type=album_type, country="US")

        albums = results["items"]

        # indexing all pages of results
        while results["next"]:
            results = self.spotify.next(results)
            albums.extend(results["items"])

        return albums

    def write_all_albums(self, albums, target_file=None):
        """
        This function gets all albums from an artist and writes it to a file in the
        current working directory called [ARTIST].txt, where [ARTIST] is the artist
        of the album
        :param artist_uri - spotify artist uri
        :param target_file - file to write albums to
        """

        # if no file if given, the default save file is in the current working
        # directory with the name of the artist
        if target_file is None:
            target_file = albums[0]["artists"][0]["name"] + ".txt"

        for album in albums:
            logger.info('Fetching album "{album}".'.format(album=album["name"]))
            self.write_album_tracks(album, target_file=target_file)

    def write_tracks(self, tracks, target_file):
        def writer(tracks, file_io):
            track_urls = []
            while True:
                for item in tracks["items"]:
                    if "track" in item:
                        track = item["track"]
                    else:
                        track = item
                    # Spotify sometimes returns additional empty "tracks" in the API
                    # response. We need to discard such "tracks".
                    # See https://github.com/spotify/web-api/issues/1562
                    if track is None:
                        continue
                    try:
                        track_url = track["external_urls"]["spotify"]
                        file_io.write(track_url + "\n")
                        track_urls.append(track_url)
                    except KeyError:
                        # FIXME: Write "{artist} - {name}" instead of Spotify URI for
                        #        "local only" tracks.
                        logger.warning(
                            'Skipping track "{0}" by "{1}" (local only?)'.format(
                                track["name"], track["artists"][0]["name"]
                            )
                        )
                # 1 page = 50 results
                # check if there are more pages
                if tracks["next"]:
                    tracks = self.spotify.next(tracks)
                else:
                    break
            return track_urls

        logger.info(u"Writing {0} tracks to {1}.".format(tracks["total"], target_file))
        write_to_stdout = target_file == "-"
        if write_to_stdout:
            file_out = sys.stdout
            track_urls = writer(tracks, file_out)
        else:
            with open(target_file, "a") as file_out:
                track_urls = writer(tracks, file_out)
        return track_urls

