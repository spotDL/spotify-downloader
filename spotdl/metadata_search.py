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


def prompt_for_youtube_search_result(videos):
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
        track_type_mapper = {
            "spotify": self._on_youtube_and_spotify_for_type_spotify,
            "youtube": self._on_youtube_and_spotify_for_type_youtube,
            "query": self._on_youtube_and_spotify_for_type_query,
        }
        caller = track_type_mapper[self.track_type]
        metadata = caller()

        if not self.lyrics:
            return metadata

        lyric_query = self._make_lyric_search_query(metadata)
        metadata["lyrics"] = spotdl.util.ThreadWithReturnValue(
            target=self.get_lyrics,
            args=(lyric_query,),
        )

        return metadata

    def on_youtube(self):
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
            video = prompt_for_youtube_search_result(videos)
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
        spotify_metadata = self._on_spotify_for_type_spotify(self.track)
        search_query = spotdl.metadata.format_string(self.yt_search_format, spotify_metadata)
        video = self._best_on_youtube_search_for_type_query(search_query)
        return video

    def _on_youtube_and_spotify_for_type_spotify(self):
        logger.debug("Extracting YouTube and Spotify metadata for input Spotify URI.")
        spotify_metadata = self._on_spotify_for_type_spotify(self.track)
        search_query = spotdl.metadata.format_string(self.yt_search_format, spotify_metadata)
        youtube_video = self._best_on_youtube_search_for_type_spotify(search_query)
        youtube_metadata = self.providers["youtube"].from_url(youtube_video["url"])
        metadata = spotdl.util.merge_copy(
            youtube_metadata,
            spotify_metadata
        )
        return metadata

    def _on_youtube_and_spotify_for_type_youtube(self):
        logger.debug("Extracting YouTube and Spotify metadata for input YouTube URL.")
        youtube_metadata = self._on_youtube_for_type_youtube(self.track)
        search_query = spotdl.metadata.format_string("{track-name}", youtube_metadata)
        spotify_metadata = self._on_spotify_for_type_query(search_query)
        metadata = spotdl.util.merge_copy(
            youtube_metadata,
            spotify_metadata
        )
        return metadata

    def _on_youtube_and_spotify_for_type_query(self):
        logger.debug("Extracting YouTube and Spotify metadata for input track query.")
        search_query = self.track
        # Make use of threads here to search on both YouTube & Spotify
        # at the same time.
        spotify_metadata = spotdl.util.ThreadWithReturnValue(
            target=self._on_spotify_for_type_query,
            args=(search_query,)
        )
        spotify_metadata.start()
        youtube_metadata = self._on_youtube_for_type_query(search_query)
        metadata = spotdl.util.merge_copy(
            youtube_metadata,
            spotify_metadata.join()
        )
        return metadata

    def _on_youtube_for_type_spotify(self):
        logger.debug("Extracting YouTube metadata for input Spotify URI.")
        spotify_metadata = self._on_spotify_for_type_spotify(self.track)
        search_query = spotdl.metadata.format_string(self.yt_search_format, spotify_metadata)
        youtube_video = self._best_on_youtube_search_for_type_spotify(search_query)
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

