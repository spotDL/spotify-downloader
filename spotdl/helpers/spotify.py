# XXX: Perhaps we do not need to call `spotify._get_id`
#      explicitly in newer versions of spotipy.
#      Need to confirm this and if so, remove the calls
#      to `spotify._get_id` in below methods.

from spotdl.authorize.services import AuthorizeSpotify

class SpotifyHelpers:
    def __init__(self, spotify=None):
        if spotify is None:
            spotify = AuthorizeSpotify()
        self.spotify = spotify

    def prompt_for_user_playlist(self, username):
        """ Write user playlists to text_file """
        links = fetch_user_playlist_urls(username)
        playlist = internals.input_link(links)
        return playlist

    def fetch_user_playlist_urls(self, username):
        """ Fetch user playlists when using the -u option. """
        playlists = self.spotify.user_playlists(username)
        links = []
        check = 1

        while True:
            for playlist in playlists["items"]:
                # in rare cases, playlists may not be found, so playlists['next']
                # is None. Skip these. Also see Issue #91.
                if playlist["name"] is not None:
                    # log.info(
                    #     u"{0:>5}. {1:<30}  ({2} tracks)".format(
                    #         check, playlist["name"], playlist["tracks"]["total"]
                    #     )
                    # )
                    playlist_url = playlist["external_urls"]["spotify"]
                    # log.debug(playlist_url)
                    links.append(playlist_url)
                    check += 1
            if playlists["next"]:
                playlists = self.spotify.next(playlists)
            else:
                break

        return links

    def fetch_playlist(self, playlist_url):
        try:
            playlist_id = self.spotify._get_id("playlist", playlist_url)
        except IndexError:
            # Wrong format, in either case
            # log.error("The provided playlist URL is not in a recognized format!")
            sys.exit(10)
        try:
            results = self.spotify.user_playlist(
                user=None, playlist_id=playlist_id, fields="tracks,next,name"
            )
        except spotipy.client.SpotifyException:
            # log.error("Unable to find playlist")
            # log.info("Make sure the playlist is set to publicly visible and then try again")
            sys.exit(11)

        return results

    def write_playlist(self, playlist, text_file=None):
        tracks = playlist["tracks"]
        if not text_file:
            text_file = u"{0}.txt".format(slugify(playlist["name"], ok="-_()[]{}"))
        return write_tracks(tracks, text_file)

    def fetch_album(self, album_url):
        album_id = self.spotify._get_id("album", album_url)
        album = self.spotify.album(album_id)
        return album

    def write_album(self, album, text_file=None):
        tracks = self.spotify.album_tracks(album["id"])
        if not text_file:
            text_file = u"{0}.txt".format(slugify(album["name"], ok="-_()[]{}"))
        return write_tracks(tracks, text_file)

    def fetch_albums_from_artist(self, artist_url, album_type=None):
        """
        This function returns all the albums from a give artist_url using the US
        market
        :param artist_url - spotify artist url
        :param album_type - the type of album to fetch (ex: single) the default is
                            all albums
        :param return - the album from the artist
        """

        # fetching artist's albums limitting the results to the US to avoid duplicate
        # albums from multiple markets
        artist_id = self.spotify._get_id("artist", artist_url)
        results = self.spotify.artist_albums(artist_id, album_type=album_type, country="US")

        albums = results["items"]

        # indexing all pages of results
        while results["next"]:
            results = self.spotify.next(results)
            albums.extend(results["items"])

        return albums

    def write_all_albums_from_artist(self, albums, text_file=None):
        """
        This function gets all albums from an artist and writes it to a file in the
        current working directory called [ARTIST].txt, where [ARTIST] is the artist
        of the album
        :param artist_url - spotify artist url
        :param text_file - file to write albums to
        """

        album_base_url = "https://open.spotify.com/album/"

        # if no file if given, the default save file is in the current working
        # directory with the name of the artist
        if text_file is None:
            text_file = albums[0]["artists"][0]["name"] + ".txt"

        for album in albums:
            logging album name
            log.info("Fetching album: " + album["name"])
            write_album(album_base_url + album["id"], text_file=text_file)

    def write_tracks(self, tracks, text_file):
        # log.info(u"Writing {0} tracks to {1}".format(tracks["total"], text_file))
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
                        # log.debug(track_url)
                        file_out.write(track_url + "\n")
                        track_urls.append(track_url)
                    except KeyError:
                        # log.warning(
                            u"Skipping track {0} by {1} (local only?)".format(
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

