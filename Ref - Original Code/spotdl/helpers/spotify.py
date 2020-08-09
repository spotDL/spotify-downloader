from spotdl.authorize.services import AuthorizeSpotify
import spotdl.helpers.exceptions
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
    """
    Provides helper methods for accessing the Spotify API.

    Parameters
    ----------
    spotify: :class:`spotdl.authorize.services.AuthorizeSpotify`, :class:`spotipy.Spotify`, ``None``
        An authorized instance to make API calls to Spotify endpoints.

        If ``None``, it will attempt to reference an already created
        :class:`spotdl.authorize.services.AuthorizeSpotify` instance.
    """

    def __init__(self, spotify=None):
        if spotify is None:
            spotify = AuthorizeSpotify()
        self.spotify = spotify

    def prompt_for_user_playlist(self, username):
        """
        An interactive method that will display user's playlists
        and prompt to make a selection.

        Parameters
        ----------
        username: `str`
            Spotfiy username.

        Returns
        -------
        spotify_uri: `str`
            Spotify URI for the selected playlist.
        """
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
        """
        Fetches all user's playlists.

        Parameters
        ----------
        username: `str`
            Spotfiy username.

        Returns
        -------
        playlist_uris: `list`
            Containing all playlist URIs.
        """
        logger.debug('Fetching playlists for "{username}".'.format(username=username))
        try:
            playlists = self.spotify.user_playlists(username)
        except spotipy.client.SpotifyException:
            msg = ('Unable to find user "{}". Make sure the the user ID is correct '
                   'and then try again.'.format(username))
            logger.error(msg)
            raise spotdl.helpers.exceptions.SpotifyUserNotFoundError(msg)
        else:
            collected_playlists = []
            while True:
                for playlist in playlists["items"]:
                    # in rare cases, playlists may not be found, so playlists['next']
                    # is None. Skip these. Also see Issue #91.
                    if playlist["name"] is not None:
                        collected_playlists.append(playlist)
                if playlists["next"]:
                    playlists = self.spotify.next(playlists)
                else:
                    break
            return collected_playlists

    def fetch_playlist(self, playlist_uri):
        """
        Fetches playlist.

        Parameters
        ----------
        playlist_uri: `str`
            Spotify playlist URI.

        Returns
        -------
        playlist: `dict`
            Spotify API response object for the playlist endpoint.
        """
        logger.debug('Fetching playlist "{playlist}".'.format(playlist=playlist_uri))
        try:
            playlist = self.spotify.playlist(playlist_uri, fields="tracks,next,name")
        except spotipy.client.SpotifyException:
            msg = ('Unable to find playlist "{}". Make sure the the playlist ID is correct '
                   'and the playlist is set to publicly visible, and then try again.'.format(
                    playlist_uri
                  ))
            logger.error(msg)
            raise spotdl.helpers.exceptions.SpotifyPlaylistNotFoundError(msg)
        else:
            return playlist

    def write_playlist_tracks(self, playlist, target_path=None):
        """
        Writes playlist track URIs to file.

        Parameters
        ----------
        playlist: `dict`
            Spotify API response object for the playlist endpoint.

        target_path: `str`
            Write Spotify track URIs to this file.
        """
        tracks = playlist["tracks"]
        if not target_path:
            target_path = u"{0}.txt".format(slugify(playlist["name"], ok="-_()[]{}"))
        return self.write_tracks(tracks, target_path)

    def fetch_album(self, album_uri):
        """
        Fetches album.

        Parameters
        ----------
        album_uri: `str`
            Spotify album URI.

        Returns
        -------
        album: `dict`
            Spotify API response object for the album endpoint.
        """
        logger.debug('Fetching album "{album}".'.format(album=album_uri))
        try:
            album = self.spotify.album(album_uri)
        except spotipy.client.SpotifyException:
            msg = ('Unable to find album "{}". Make sure the album ID is correct '
                   'and then try again.'.format(album_uri))
            logger.error(msg)
            raise spotdl.helpers.exceptions.SpotifyAlbumNotFoundError(msg)
        else:
            return album

    def write_album_tracks(self, album, target_path=None):
        """
        Writes album track URIs to file.

        Parameters
        ----------
        album: `dict`
            Spotify API response object for the album endpoint.

        target_path: `str`
            Write Spotify track URIs to this file.
        """
        tracks = self.spotify.album_tracks(album["id"])
        if not target_path:
            target_path = u"{0}.txt".format(slugify(album["name"], ok="-_()[]{}"))
        return self.write_tracks(tracks, target_path)

    def fetch_albums_from_artist(self, artist_uri, album_type=None):
        """
        Fetches all Spotify albums from a Spotify artist in the US
        market.

        Parameters
        ----------
        artist_uri: `str`
            Spotify artist URI.

        album_type: `str`
            The type of album to fetch (ex: single) the default is
            all albums.

        Returns
        -------
        abums: `str`
            All albums received in the Spotify API response object.
        """
        logger.debug('Fetching all albums for "{artist}".'.format(artist=artist_uri))
        # fetching artist's albums limitting the results to the US to avoid duplicate
        # albums from multiple markets
        try:
            results = self.spotify.artist_albums(artist_uri, album_type=album_type, country="US")
        except spotipy.client.SpotifyException:
            msg = ('Unable to find artist "{}". Make sure the artist ID is correct '
                   'and then try again.'.format(artist_uri))
            logger.error(msg)
            raise spotdl.helpers.exceptions.SpotifyArtistNotFoundError(msg)
        else:
            albums = results["items"]
            # indexing all pages of results
            while results["next"]:
                results = self.spotify.next(results)
                albums.extend(results["items"])
            return albums

    def write_all_albums(self, albums, target_path=None):
        """
        Writes tracks from all albums into a file.

        Parameters
        ----------
        albums: `str`
            Spotfiy API response received in :func:`fetch_albums_from_artist`.

        target_path: `str`
            Write Spotify track URIs to this file.
        """
        # if no file if given, the default save file is in the current working
        # directory with the name of the artist
        if target_path is None:
            target_path = albums[0]["artists"][0]["name"] + ".txt"

        for album in albums:
            logger.info('Fetching album "{album}".'.format(album=album["name"]))
            self.write_album_tracks(album, target_path=target_path)

    def write_tracks(self, tracks, target_path):
        """
        Writes Spotify track URIs to file

        Parameters
        ----------
        tracks: `list`
            As returned in the Spotify API response.

        target_path: `str`
            Writes track URIs to this file.
        """
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

        logger.info(u"Writing {0} tracks to {1}.".format(tracks["total"], target_path))
        write_to_stdout = target_path == "-"
        if write_to_stdout:
            file_out = sys.stdout
            track_urls = writer(tracks, file_out)
        else:
            with open(target_path, "a") as file_out:
                track_urls = writer(tracks, file_out)
        return track_urls

