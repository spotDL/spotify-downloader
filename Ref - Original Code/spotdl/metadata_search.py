from spotdl.metadata.providers import ProviderSpotify
from spotdl.metadata.providers import ProviderYouTube
from spotdl.lyrics.providers import Genius
from spotdl.lyrics.exceptions import LyricsNotFoundError

import spotdl.metadata
import spotdl.util
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError

from spotdl.command_line.exceptions import NoYouTubeVideoFoundError
from spotdl.command_line.exceptions import NoYouTubeVideoMatchError

import sys
import logging
logger = logging.getLogger(__name__)

PROVIDERS = {
    "spotify": ProviderSpotify,
    "youtube": ProviderYouTube,
}


def _prompt_for_youtube_search_result(videos):
    max_index_length = len(str(len(videos)))
    max_title_length = max(len(v["title"]) for v in videos)
    msg = "{index:>{max_index}}. Skip downloading this track".format(
        index=0,
        max_index=max_index_length,
    )
    print(msg, file=sys.stderr)
    for index, video in enumerate(videos, 1):
        vid_details = "{index:>{max_index}}. {title:<{max_title}}\n{new_line_gap}  {url} [{duration}]".format(
            index=index,
            max_index=max_index_length,
            title=video["title"],
            max_title=max_title_length,
            new_line_gap=" " * max_index_length,
            url=video["url"],
            duration=video["duration"],
        )
        print(vid_details, file=sys.stderr)
    print("", file=sys.stderr)

    selection = spotdl.util.prompt_user_for_selection(range(1, len(videos)+1))

    if selection is None:
        return None
    return videos[selection-1]


class MetadataSearch:
    """
    A dedicated class to perform metadata searches on various
    providers.

    Parameters
    ----------
    track: `str`
        A Spotify URI, YouTube URL or a search query.

    lyrics: `bool`
        Whether or not to fetch lyrics.

    yt_search_format: `str`
        The search format for making YouTube searches (if needed).

    yt_manual: `bool`
        Whether or not to manually choose the YouTube video result.

    providers: `dict`
        Available metadata providers.

    Examples
    --------
    + Fetch track's metadata from YouTube and Spotify:

        >>> from spotdl.authorize.services import AuthorizeSpotify
        # It is necessary to authorize Spotify API otherwise API
        # calls won't pass through Spotify. That means we won't
        # be able to fetch metadata from Spotify.
        >>> AuthorizeSpotify(
        ...     client_id="your_spotify_client_id",
        ...     client_secret="your_spotify_client_secret",
        ... )
        >>>
        >>> from spotdl.metadata_search import MetadataSearch
        >>> searcher = MetadataSearch("ncs spectre")
        >>> metadata = searcher.on_youtube_and_spotify()
        >>> metadata["external_urls"]["youtube"]
        'https://youtube.com/watch?v=AOeY-nDp7hI'
        >>> metadata["external_urls"]["spotify"]
        'https://open.spotify.com/track/0K3m6DKdX9VKewdb3r5uiT'
    """

    def __init__(self, track, lyrics=False, yt_search_format="{artist} - {track-name}", yt_manual=False, providers=PROVIDERS):
        self.track = track
        self.track_type = spotdl.util.track_type(track)
        self.lyrics = lyrics
        self.yt_search_format = yt_search_format
        self.yt_manual = yt_manual
        self.providers = {}
        for provider, parent in providers.items():
            self.providers[provider] = parent()
        self.lyric_provider = Genius()

    def get_lyrics(self, query):
        """
        Internally calls :func:`spotdl.lyrics.LyricBase.from_query`
        but will warn and return ``None`` no lyrics found.

        Parameters
        ----------
        query: `str`
            The query to perform the search with.

        Returns
        -------
        lyrics: `str`, `None`
            Depending on whether the lyrics were found or not.
        """

        try:
            lyrics = self.lyric_provider.from_query(query)
        except LyricsNotFoundError as e:
            logger.warning(e.args[0])
            lyrics = None
        return lyrics

    def _make_lyric_search_query(self, metadata):
        if self.track_type == "query":
            lyric_query = self.track
        else:
            lyric_search_format = "{artist} - {track-name}"
            lyric_query = spotdl.metadata.format_string(
                lyric_search_format,
                metadata
            )
        return lyric_query

    def on_youtube_and_spotify(self):
        """
        Performs the search on both YouTube and Spotify.

        Returns
        -------
        metadata: `dict`
            Combined metadata in standardized form, with Spotify
            overriding any same YouTube metadata values. If ``lyrics``
            was ``True`` in :class:`MetadataSearch`, call
            ``metadata["lyrics"].join()`` to access them.
        """

        track_type_mapper = {
            "spotify": self._on_youtube_and_spotify_for_type_spotify,
            "youtube": self._on_youtube_and_spotify_for_type_youtube,
            "query": self._on_youtube_and_spotify_for_type_query,
        }
        caller = track_type_mapper[self.track_type]
        metadata = caller(self.track)

        if not self.lyrics:
            return metadata

        lyric_query = self._make_lyric_search_query(metadata)
        metadata["lyrics"] = spotdl.util.ThreadWithReturnValue(
            target=self.get_lyrics,
            args=(lyric_query,),
        )

        return metadata

    def on_youtube(self):
        """
        Performs the search on YouTube.

        Returns
        -------
        metadata: `dict`
            Metadata in standardized form. If ``lyrics`` was ``True`` in
            :class:`MetadataSearch`, call ``metadata["lyrics"].join()``
            to access them.
        """

        track_type_mapper = {
            "spotify": self._on_youtube_for_type_spotify,
            "youtube": self._on_youtube_for_type_youtube,
            "query": self._on_youtube_for_type_query,
        }
        caller = track_type_mapper[self.track_type]
        metadata = caller(self.track)

        if not self.lyrics:
            return metadata

        lyric_query = self._make_lyric_search_query(metadata)
        metadata["lyrics"] = spotdl.util.ThreadWithReturnValue(
            target=self.get_lyrics,
            arguments=(lyric_query,),
        )

        return metadata

    def on_spotify(self):
        """
        Performs the search on Spotify.

        Returns
        -------
        metadata: `dict`
            Metadata in standardized form. If ``lyrics`` was ``True`` in
            :class:`MetadataSearch`, call ``metadata["lyrics"].join()``
            to access them.
        """

        track_type_mapper = {
            "spotify": self._on_spotify_for_type_spotify,
            "youtube": self._on_spotify_for_type_youtube,
            "query": self._on_spotify_for_type_query,
        }
        caller = track_type_mapper[self.track_type]
        metadata = caller(self.track)

        if not self.lyrics:
            return metadata

        lyric_query = self._make_lyric_search_query(metadata)
        metadata["lyrics"] = spotdl.util.ThreadWithReturnValue(
            target=self.get_lyrics,
            arguments=(lyric_query,),
        )

        return metadata

    def best_on_youtube_search(self):
        """
        Performs a search on YouTube returning the most relevant video.

        Returns
        -------
        video: `dict`
            Contains the keys: *title*, *url* and *duration*.
        """

        track_type_mapper = {
            "spotify": self._best_on_youtube_search_for_type_spotify,
            "youtube": self._best_on_youtube_search_for_type_youtube,
            "query": self._best_on_youtube_search_for_type_query,
        }
        caller = track_type_mapper[self.track_type]
        video = caller(self.track)
        return video

    def _best_on_youtube_search_for_type_query(self, query):
        videos = self.providers["youtube"].search(query)
        if not videos:
            raise NoYouTubeVideoFoundError(
                'YouTube returned no videos for the search query "{}".'.format(query)
            )
        if self.yt_manual:
            video = _prompt_for_youtube_search_result(videos)
        else:
            video = videos.bestmatch()

        if video is None:
            raise NoYouTubeVideoMatchError(
                'No matching videos found on YouTube for the search query "{}".'.format(
                    query
                )
            )
        return video

    def _best_on_youtube_search_for_type_youtube(self, url):
        video = self._best_on_youtube_search_for_type_query(url)
        return video

    def _best_on_youtube_search_for_type_spotify(self, url):
        spotify_metadata = self._on_spotify_for_type_spotify(url)
        search_query = spotdl.metadata.format_string(self.yt_search_format, spotify_metadata)
        video = self._best_on_youtube_search_for_type_query(search_query)
        return video

    def _on_youtube_and_spotify_for_type_spotify(self, url):
        logger.debug("Extracting YouTube and Spotify metadata for input Spotify URI.")
        spotify_metadata = self._on_spotify_for_type_spotify(url)
        search_query = spotdl.metadata.format_string(self.yt_search_format, spotify_metadata)
        youtube_video = self._best_on_youtube_search_for_type_query(search_query)
        youtube_metadata = self.providers["youtube"].from_url(youtube_video["url"])
        metadata = spotdl.util.merge_copy(
            youtube_metadata,
            spotify_metadata
        )
        return metadata

    def _on_youtube_and_spotify_for_type_youtube(self, url):
        logger.debug("Extracting YouTube and Spotify metadata for input YouTube URL.")
        youtube_metadata = self._on_youtube_for_type_youtube(url)
        search_query = spotdl.metadata.format_string("{track-name}", youtube_metadata)
        spotify_metadata = self._on_spotify_for_type_query(search_query)
        metadata = spotdl.util.merge_copy(
            youtube_metadata,
            spotify_metadata
        )
        return metadata

    def _on_youtube_and_spotify_for_type_query(self, query):
        logger.debug("Extracting YouTube and Spotify metadata for input track query.")
        # Make use of threads here to search on both YouTube & Spotify
        # at the same time.
        spotify_metadata = spotdl.util.ThreadWithReturnValue(
            target=self._on_spotify_for_type_query,
            args=(query,)
        )
        spotify_metadata.start()
        youtube_metadata = self._on_youtube_for_type_query(query)
        metadata = spotdl.util.merge_copy(
            youtube_metadata,
            spotify_metadata.join()
        )
        return metadata

    def _on_youtube_for_type_spotify(self, url):
        logger.debug("Extracting YouTube metadata for input Spotify URI.")
        youtube_video = self._best_on_youtube_search_for_type_spotify(url)
        youtube_metadata = self.providers["youtube"].from_url(youtube_video["url"])
        return youtube_metadata

    def _on_youtube_for_type_youtube(self, url):
        logger.debug("Extracting YouTube metadata for input YouTube URL.")
        youtube_metadata = self.providers["youtube"].from_url(url)
        return youtube_metadata

    def _on_youtube_for_type_query(self, query):
        logger.debug("Extracting YouTube metadata for input track query.")
        youtube_video = self._best_on_youtube_search_for_type_query(query)
        youtube_metadata = self.providers["youtube"].from_url(youtube_video["url"])
        return youtube_metadata

    def _on_spotify_for_type_youtube(self, url):
        logger.debug("Extracting Spotify metadata for input YouTube URL.")
        youtube_metadata = self.providers["youtube"].from_url(url)
        search_query = spotdl.metadata.format_string("{track-name}", youtube_metadata)
        spotify_metadata = self.providers["spotify"].from_query(search_query)
        return spotify_metadata

    def _on_spotify_for_type_spotify(self, url):
        logger.debug("Extracting Spotify metadata for input Spotify URI.")
        spotify_metadata = self.providers["spotify"].from_url(url)
        return spotify_metadata

    def _on_spotify_for_type_query(self, query):
        logger.debug("Extracting Spotify metadata for input track query.")
        try:
            spotify_metadata = self.providers["spotify"].from_query(query)
        except SpotifyMetadataNotFoundError as e:
            logger.warn(e.args[0])
            spotify_metadata = {}
        return spotify_metadata

