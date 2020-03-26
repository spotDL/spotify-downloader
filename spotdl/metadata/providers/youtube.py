import pytube
from bs4 import BeautifulSoup

import urllib.request

from spotdl.metadata import StreamsBase
from spotdl.metadata import ProviderBase
from spotdl.metadata.exceptions import YouTubeMetadataNotFoundError

BASE_URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q={}"


class YouTubeSearch:
    def __init__(self):
        self.base_url = BASE_URL

    def generate_search_url(self, query):
        quoted_query = urllib.request.quote(query)
        return self.base_url.format(quoted_query)

    def _fetch_response_html(self, url):
        response = urllib.request.urlopen(url)
        soup = BeautifulSoup(response.read(), "html.parser")
        return soup

    def _fetch_search_results(self, html):
        results = html.find_all(
            "div", {"class": "yt-lockup-dismissable yt-uix-tile"}
        )
        return results

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

        video = not not_video
        return video

    def _parse_video_id(self, result):
        details = result.find("div", class_="yt-lockup-content")
        video_id = details.find("a")["href"][-11:]
        return video_id

    def search(self, query, limit=10, tries_remaining=5):
        """ Search and scrape YouTube to return a list of matching videos. """
        # prevents an infinite loop but allows for a few retries
        if tries_remaining == 0:
            # log.debug("No tries left. I quit.")
            return

        search_url = self.generate_search_url(query)
        # log.debug("Opening URL: {0}".format(search_url))
        html = self._fetch_response_html(search_url)

        videos = []
        for result in self._fetch_search_results(html):
            if not self._is_video(result):
                continue
            if len(videos) >= limit:
                break
            video_id = self._parse_video_id(result)
            videos.append("https://www.youtube.com/watch?v=" + video_id)

        return videos


class YouTubeStreams(StreamsBase):
    def __init__(self, streams):
        audiostreams = streams.filter(only_audio=True).order_by("abr").desc()
        self.all = [{
            # Store only the integer part. For example the given
            # bitrate would be "192kbps", we store only the integer
            # part here and drop the rest.
            "bitrate": int(stream.abr[:-4]),
            "download_url": stream.url,
            "encoding": stream.audio_codec,
            "filesize": stream.filesize,
        } for stream in audiostreams]

    def getbest(self):
        return self.all[0]

    def getworst(self):
        return self.all[-1]


class ProviderYouTube(ProviderBase):
    def from_query(self, query):
        watch_urls = YouTubeSearch().search(query)
        if not watch_urls:
            raise YouTubeMetadataNotFoundError(
                'YouTube returned nothing for the given search '
                'query ("{}")'.format(query)
            )
        return self.from_url(watch_urls[0])

    def from_url(self, url):
        content = pytube.YouTube(url)
        return self.from_pytube_object(content)

    def from_pytube_object(self, content):
        return self.metadata_to_standard_form(content)

    def _fetch_publish_date(self, content):
        # FIXME: This needs to be supported in PyTube itself
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
