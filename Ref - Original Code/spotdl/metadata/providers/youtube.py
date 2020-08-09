import pytube
from bs4 import BeautifulSoup
import json

import urllib.request
import threading
from collections.abc import Sequence

from spotdl.metadata import StreamsBase
from spotdl.metadata import ProviderBase
from spotdl.metadata.exceptions import YouTubeMetadataNotFoundError

import spotdl.util

import spotdl.patch
spotdl.patch.youtube.apply_patches()

import logging
logger = logging.getLogger(__name__)

BASE_SEARCH_URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q={}"
HEADERS = [('Range', 'bytes=0-'),]


class YouTubeVideos(Sequence):
    """
    A class for dealing with YouTube videos.

    Parameters
    ----------
    videos: A `list` of `dict` video objects
    """

    def __init__(self, videos):
        self.videos = videos
        super().__init__()

    def __repr__(self):
        return "YouTubeVideos({})".format(self.videos)

    def __len__(self):
        return len(self.videos)

    def __getitem__(self, index):
        return self.videos[index]

    def __eq__(self, instance):
        return self.videos == instance.videos

    def bestmatch(self):
        """
        Returns
        -------
        video: `dict`
            A *dict* with the keys: *title*, *url* and *duration*.
        """

        video = self.videos[0]
        logger.debug("Matched with: {title} ({url}) [{duration}]".format(
            title=video["title"],
            url=video["url"],
            duration=video["duration"]
        ))
        return video


class YouTubeSearch:
    """
    Make query searches on YouTube and fetch resulting videos.

    Examples
    --------
    >>> from spotdl.metadata.providers.youtube import YouTubeSearch
    >>> youtube = YouTubeSearch()
    >>> results = youtube.search("python projects")
    >>> for result in results:
    ...     print(result["title"])
    ...     print(result["url"])
    ...     print(result["duration"])
    ...     print("")
    """

    def __init__(self):
        self.base_search_url = BASE_SEARCH_URL

    def generate_search_url(self, query):
        """
        Generates a search URL for YouTube for a given search query.

        Parameters
        ----------
        query: `str`
            The search query.

        Returns
        -------
        search_url: `str`
            A URL which corresponds to YouTube search results.
        """

        quoted_query = urllib.request.quote(query)
        search_url = self.base_search_url.format(quoted_query)
        return search_url

    def _fetch_response_html(self, url):
        response = urllib.request.urlopen(url)
        soup = BeautifulSoup(response.read(), "html.parser")
        return soup

    def _fetch_search_results_from_html(self, html, limit=10):
        videos = []
        for result in html:
            if not self._html_is_video(result):
                continue
            video = self._extract_video_details_from_html_result(result)
            videos.append(video)
            if len(videos) >= limit:
                break
        return videos

    def _extract_video_details_from_html_result(self, html):
        video_time = html.find("span", class_="video-time").get_text()
        inner_html = html.find("div", class_="yt-lockup-content")
        video_id = inner_html.find("a")["href"][-11:]
        video_title = inner_html.find("a")["title"]
        video_details = {
            "url": "https://www.youtube.com/watch?v=" + video_id,
            "title": video_title,
            "duration": video_time,
        }
        return video_details

    def _html_is_video(self, result):
        # ensure result is not a channel
        not_video = (
            result.find("channel") is not None
            or "yt-lockup-channel" in result.parent.attrs["class"]
            or "yt-lockup-channel" in result.attrs["class"]
        )
        # ensure result is not a mix/playlist
        not_video = not_video or "yt-lockup-playlist" in result.parent.attrs["class"]
        # ensure video result is not an advertisement
        not_video = not_video or result.find("googleads") is not None
        # ensure video result is not a live stream
        not_video = not_video or result.find("span", class_="video-time") is None
        video = not not_video
        return video

    def _fetch_search_results_from_json(self, json, limit=10):
        json = json["contents"]["twoColumnSearchResultsRenderer"]
        json = json["primaryContents"]["sectionListRenderer"]["contents"][0]
        json = json["itemSectionRenderer"]["contents"]
        videos = []
        for result in json:
            if not self._json_is_video(result):
                continue
            video = self._extract_video_details_from_json_result(result)
            videos.append(video)
            if len(videos) >= limit:
                break
        return videos

    def _extract_video_details_from_json_result(self, json):
        json = json["videoRenderer"]
        video_id = json["videoId"]
        video_title = json["title"]["runs"][0]["text"]
        video_time = json["lengthText"]["simpleText"]
        video_details = {
            "url": "https://www.youtube.com/watch?v=" + video_id,
            "title": video_title,
            "duration": video_time,
        }
        return video_details

    def _json_is_video(self, result):
        # ensure result is not a corrected search query
        video = "videoRenderer" in result
        return video

    def _fetch_search_results(self, html, limit=10):
        videos_html = html.find_all(
            "div", {"class": "yt-lockup-dismissable yt-uix-tile"}
        )
        if videos_html:
            return self._fetch_search_results_from_html(videos_html, limit=limit)

        # Sometimes YouTube can go crazy and return JSON data instead
        # of an HTML response. Handle such cases.
        logger.debug("YouTube returned malformed HTML. Attempting to parse possible JSON data.")

        html = str(html)
        search_start = 'window["ytInitialData"] = '
        videos_json_start = html.find(search_start) + len(search_start)
        search_end = "}}]}}}}}}"
        videos_json_end = videos_json_start + html[videos_json_start:].find(search_end) + len(search_end)
        videos_json = html[videos_json_start:videos_json_end] + "}"
        try:
            videos_json = json.loads(videos_json)
        except json.decoder.JSONDecodeError:
            return []

        return self._fetch_search_results_from_json(videos_json, limit=limit)

    def _is_server_side_invalid_response(self, videos, html):
        if videos:
            return False
        search_message = html.find("div", {"class":"search-message"})
        return search_message is None

    def search(self, query, limit=10, retries=2):
        """
        Search and scrape YouTube to return a list of matching videos.

        Parameters
        ----------
        query: `str`
            The search query.

        limit: `int`
            Return only first n results.

        retries: `int`
            YouTube can sometimes return invalid response. Maximum
            number of retries to make in such case.

        Returns
        -------
        videos: An instance of :class:`spotdl.metadata.providers.youtube.YouTubeVideos`.
        """

        search_url = self.generate_search_url(query)
        logger.debug('Fetching YouTube results for "{}" at "{}".'.format(query, search_url))
        html = self._fetch_response_html(search_url)
        videos = self._fetch_search_results(html, limit=limit)
        to_retry = retries > 0 and self._is_server_side_invalid_response(videos, html)
        if to_retry:
            logger.debug(
                "Retrying since YouTube returned invalid response for search "
                "results. Retries left: {retries}.".format(retries=retries)
            )
            return self.search(query, limit=limit, retries=retries-1)
        videos = YouTubeVideos(videos)
        return videos


class YouTubeStreams(StreamsBase):
    """
    A class for standardizing pytube YouTube streams.
    The standardized streams can be accessed by ``self.streams``,
    which is a list of streams.
    Each stream contains the keys: *bitrate*, *connection*,
    *download_url*, *encoding* and *filesize*.

    Parameters
    ----------
    streams: :class:`pytube.query.StreamQuery`
        PyTube streams.

    Examples
    --------
    >>> import pytube
    >>> video = pytube.YouTube("https://www.youtube.com/watch?v=XpmeVNxZ-Ks")
    >>> from spotdl.metadata.providers.youtube import YouTubeStreams
    >>> streams = YouTubeStreams(video.streams)
    >>> for stream in streams:
    ...     print(stream["encoding"], stream["filesize"])
    """

    def __init__(self, streams):
        self.network_headers = HEADERS
        audiostreams = streams.filter(only_audio=True).order_by("abr").desc()
        thread_pool = []
        self.streams = []
        for stream in audiostreams:
            encoding = "m4a" if "mp4a" in stream.audio_codec else stream.audio_codec
            standard_stream = {
                # Store only the integer part for bitrate. For example
                # the given bitrate would be "192kbps", we store only
                # the integer part (192) here and drop the rest.
                "bitrate": int(stream.abr[:-4]),
                "connection": None,
                "download_url": stream.url,
                "encoding": encoding,
                "filesize": None,
            }
            establish_connection = threading.Thread(
               target=self._store_connection,
               args=(standard_stream,),
            )
            thread_pool.append(establish_connection)
            establish_connection.start()
            self.streams.append(standard_stream)

        for thread in thread_pool:
            thread.join()

    def _store_connection(self, stream):
        response = self._make_request(stream["download_url"])
        stream["connection"] = response
        stream["filesize"] = int(response.headers["Content-Length"])

    def _make_request(self, url):
        request = urllib.request.Request(url)
        for header in self.network_headers:
            request.add_header(*header)
        return urllib.request.urlopen(request)

    def get(self, quality="best", preftype="automatic"):
        """
        Fetches a stream matching the given parameters.

        Parameters
        ----------
        quality: `str`
            Stream quality to fetch. Can either be "best" or "worst".

        preftype: `str`
            Stream encoding to prefer.

        Returns
        -------
        stream: `dict`, `None`
            The stream matching the given parameters. ``None`` if no
            matching stream was found.
        """

        if quality == "best":
            return self.getbest(preftype=preftype)
        elif quality == "worst":
            return self.getworst(preftype=preftype)
        else:
            return None

    def getbest(self, preftype="automatic"):
        """
        Fetches the best quality stream.

        Parameters
        ----------
        preftype: `str`
            Stream encoding to prefer.

        Returns
        -------
        stream: `dict`, `None`
            The stream matching the given parameters.
        """

        selected_stream = None
        if preftype == "automatic":
            selected_stream = self.streams[0]
        else:
            for stream in self.streams:
                if stream["encoding"] == preftype:
                    selected_stream = stream
                    break
        logger.debug('Selected best quality stream for "{preftype}" format:\n{stream}'.format(
            preftype=preftype,
            stream=selected_stream,
        ))
        return selected_stream

    def getworst(self, preftype="automatic"):
        """
        Fetches the worst quality stream.

        Parameters
        ----------
        preftype: `str`
            Stream encoding to prefer.

        Returns
        -------
        stream: `dict`, `None`
            The stream matching the given parameters.
        """

        selected_stream = None
        if preftype == "automatic":
            selected_stream = self.streams[-1]
        else:
            for stream in self.streams[::-1]:
                if stream["encoding"] == preftype:
                    selected_stream = stream
                    break
        logger.debug('Selected worst quality stream for "{preftype}" format:\n{stream}'.format(
            preftype=preftype,
            stream=selected_stream,
        ))
        return selected_stream


class ProviderYouTube(ProviderBase):
    """
    Fetch metadata from YouTube in standardized form.

    Examples
    --------
    + Making a YouTube search and fetching metadata for the first
      result

        >>> from spotdl.metadata.providers import ProviderYouTube
        >>> provider = ProviderYouTube()
        >>> metadata = provider.from_query("mitis - try (unreleased)")
        >>> metadata["name"]
        'MitiS - Try (Unreleased) ft RØRY'
    """

    def from_query(self, query, retries=5):
        watch_urls = self.search(query)
        if not watch_urls:
            raise YouTubeMetadataNotFoundError(
                'YouTube returned nothing for the given search '
                'query ("{}")'.format(query)
            )
        return self.from_url(watch_urls[0]["url"], retries=retries)

    def from_url(self, url, retries=5):
        logger.debug('Fetching YouTube metadata for "{url}".'.format(url=url))
        try:
            content = pytube.YouTube(url)
        except KeyError:
            # Sometimes YouTube can return unexpected response, in such a case
            # retry a few times before finally failing.
            if retries > 0:
                retries -= 1
                logger.debug(
                    "YouTube returned an unexpected response for "
                    "`pytube.YouTube({url})`. Retries left: {retries}".format(
                        url=url, retries=retries
                    )
                )
                return self.from_url(url, retries=retries)
            else:
                raise
        else:
            return self.from_pytube_object(content)

    def from_pytube_object(self, content):
        return self._metadata_to_standard_form(content)

    def search(self, query):
        return YouTubeSearch().search(query)

    def _fetch_publish_date(self, content):
        # XXX: This needs to be supported in PyTube itself
        # See https://github.com/nficano/pytube/issues/595
        position = content.watch_html.find("publishDate")
        publish_date = content.watch_html[position+16:position+25]
        return publish_date

    def _metadata_to_standard_form(self, content):
        publish_date = self._fetch_publish_date(content)
        metadata = {
            "name": content.title,
            "artists": [{"name": content.author}],
            "duration": content.length,
            "external_urls": {"youtube": content.watch_url},
            "album": {
                "images": [{"url": content.thumbnail_url}],
                "artists": [{"name": None}],
                "name": None,
            },
            "year": publish_date.split("-")[0],
            "release_date": publish_date,
            "type": "track",
            "disc_number": 1,
            "track_number": 1,
            "total_tracks": 1,
            "publisher": None,
            "external_ids": {"isrc": None},
            "lyrics": None,
            "copyright": None,
            "genre": None,
            "streams": YouTubeStreams(content.streams),
            "provider": "youtube",
        }
        return metadata
