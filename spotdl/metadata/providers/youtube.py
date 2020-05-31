import pytube
from bs4 import BeautifulSoup

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
        video = self.videos[0]
        logger.debug("Matched with: {title} ({url}) [{duration}]".format(
            title=video["title"],
            url=video["url"],
            duration=video["duration"]
        ))
        return video


class YouTubeSearch:
    def __init__(self):
        self.base_search_url = BASE_SEARCH_URL

    def generate_search_url(self, query):
        quoted_query = urllib.request.quote(query)
        return self.base_search_url.format(quoted_query)

    def _fetch_response_html(self, url):
        response = urllib.request.urlopen(url)
        soup = BeautifulSoup(response.read(), "html.parser")
        return soup

    def _extract_video_details_from_result(self, html):
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

    def _fetch_search_results(self, html, limit=10):
        result_source = html.find_all(
            "div", {"class": "yt-lockup-dismissable yt-uix-tile"}
        )
        videos = []

        for result in result_source:
            if not self._is_video(result):
                continue

            video = self._extract_video_details_from_result(result)
            videos.append(video)

            if len(videos) >= limit:
                break

        return videos

    def _is_video(self, result):
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

    def _is_server_side_invalid_response(self, videos, html):
        if videos:
            return False
        search_message = html.find("div", {"class":"search-message"})
        return search_message is None

    def search(self, query, limit=10, retries=5):
        """ Search and scrape YouTube to return a list of matching videos. """
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
        return YouTubeVideos(videos)


class YouTubeStreams(StreamsBase):
    def __init__(self, streams):
        self.network_headers = HEADERS

        audiostreams = streams.filter(only_audio=True).order_by("abr").desc()

        thread_pool = []
        self.all = []

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
            self.all.append(standard_stream)

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
        if quality == "best":
            return self.getbest(preftype=preftype)
        elif quality == "worst":
            return self.getworst(preftype=preftype)
        else:
            return None

    def getbest(self, preftype="automatic"):
        selected_stream = None
        if preftype == "automatic":
            selected_stream = self.all[0]
        else:
            for stream in self.all:
                if stream["encoding"] == preftype:
                    selected_stream = stream
                    break
        logger.debug('Selected best quality stream for "{preftype}" format:\n{stream}'.format(
            preftype=preftype,
            stream=selected_stream,
        ))
        return selected_stream

    def getworst(self, preftype="automatic"):
        selected_stream = None
        if preftype == "automatic":
            selected_stream = self.all[-1]
        else:
            for stream in self.all[::-1]:
                if stream["encoding"] == preftype:
                    selected_stream = stream
                    break
        logger.debug('Selected worst quality stream for "{preftype}" format:\n{stream}'.format(
            preftype=preftype,
            stream=selected_stream,
        ))
        return selected_stream


class ProviderYouTube(ProviderBase):
    def from_query(self, query):
        watch_urls = self.search(query)
        if not watch_urls:
            raise YouTubeMetadataNotFoundError(
                'YouTube returned nothing for the given search '
                'query ("{}")'.format(query)
            )
        return self.from_url(watch_urls[0])

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
        return self.metadata_to_standard_form(content)

    def search(self, query):
        return YouTubeSearch().search(query)

    def _fetch_publish_date(self, content):
        # XXX: This needs to be supported in PyTube itself
        # See https://github.com/nficano/pytube/issues/595
        position = content.watch_html.find("publishDate")
        publish_date = content.watch_html[position+16:position+25]
        return publish_date

    def metadata_to_standard_form(self, content):
        """ Fetch a song's metadata from YouTube. """
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
