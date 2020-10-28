# -*- coding: utf-8 -*-
"""Module to download a complete playlist from a youtube channel."""
import json
import logging
import re
from collections.abc import Sequence
from datetime import date
from datetime import datetime
from typing import Dict, Tuple
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import parse_qs

from pytube import request
from pytube import YouTube
from pytube.helpers import cache
from pytube.helpers import deprecated
from pytube.helpers import install_proxy
from pytube.helpers import uniqueify

logger = logging.getLogger(__name__)


class Playlist(Sequence):
    """Load a YouTube playlist with URL or ID"""

    def __init__(self, url: str, proxies: Optional[Dict[str, str]] = None):
        if proxies:
            install_proxy(proxies)

        try:
            self.playlist_id: str = parse_qs(url.split("?")[1])["list"][0]
        except IndexError:  # assume that url is just the id
            self.playlist_id = url

        self.playlist_url = (
            f"https://www.youtube.com/playlist?list={self.playlist_id}"
        )
        self.html = request.get(self.playlist_url)

        # Needs testing with non-English
        self.last_update: Optional[date] = None
        date_match = re.search(
            r"Last updated on (\w{3}) (\d{1,2}), (\d{4})", self.html
        )
        if date_match:
            month, day, year = date_match.groups()
            self.last_update = datetime.strptime(
                f"{month} {day:0>2} {year}", "%b %d %Y"
            ).date()

        self._js_regex = re.compile(r"window\[\"ytInitialData\"] = ([^\n]+)")

        self._video_regex = re.compile(r"href=\"(/watch\?v=[\w-]*)")

    @deprecated(
        "This function will be removed in the future, please use .video_urls"
    )
    def parse_links(self) -> List[str]:  # pragma: no cover
        """ Deprecated function for returning list of URLs

        :return: List[str]
        """
        return self.video_urls

    def _extract_json(self, html: str) -> str:
        return self._js_regex.search(html).group(1)[0:-1]

    def _paginate(
        self, until_watch_id: Optional[str] = None
    ) -> Iterable[List[str]]:
        """Parse the video links from the page source, yields the /watch?v=
        part from video link

        :param until_watch_id Optional[str]: YouTube Video watch id until
            which the playlist should be read.

        :rtype: Iterable[List[str]]
        :returns: Iterable of lists of YouTube watch ids
        """
        req = self.html
        videos_urls, continuation = self._extract_videos(
            # extract the json located inside the window["ytInitialData"] js
            # variable of the playlist html page
            self._extract_json(req)
        )
        if until_watch_id:
            try:
                trim_index = videos_urls.index(f"/watch?v={until_watch_id}")
                yield videos_urls[:trim_index]
                return
            except ValueError:
                pass
        yield videos_urls

        # Extraction from a playlist only returns 100 videos at a time
        # if self._extract_videos returns a continuation there are more
        # than 100 songs inside a playlist, so we need to add further requests
        # to gather all of them
        if continuation:
            load_more_url, headers = self._build_continuation_url(continuation)
        else:
            load_more_url, headers = None, None

        while load_more_url and headers:  # there is an url found
            logger.debug("load more url: %s", load_more_url)
            # requesting the next page of videos with the url generated from the
            # previous page
            req = request.get(load_more_url, extra_headers=headers)
            # extract up to 100 songs from the page loaded
            # returns another continuation if more videos are available
            videos_urls, continuation = self._extract_videos(req)
            if until_watch_id:
                try:
                    trim_index = videos_urls.index(f"/watch?v={until_watch_id}")
                    yield videos_urls[:trim_index]
                    return
                except ValueError:
                    pass
            yield videos_urls

            if continuation:
                load_more_url, headers = self._build_continuation_url(
                    continuation
                )
            else:
                load_more_url, headers = None, None

    @staticmethod
    def _build_continuation_url(continuation: str) -> Tuple[str, dict]:
        """Helper method to build the url and headers required to request
        the next page of videos

        :param str continuation: Continuation extracted from the json response
            of the last page
        :rtype: Tuple[str, dict]
        :returns: Tuple of an url and required headers for the next http
            request
        """
        return (
            (
                f"https://www.youtube.com/browse_ajax?ctoken="
                f"{continuation}&continuation={continuation}"
            ),
            {
                "X-YouTube-Client-Name": "1",
                "X-YouTube-Client-Version": "2.20200720.00.02",
            },
        )

    @staticmethod
    def _extract_videos(raw_json: str) -> Tuple[List[str], Optional[str]]:
        """Extracts videos from a raw json page

        :param str raw_json: Input json extracted from the page or the last
            server response
        :rtype: Tuple[List[str], Optional[str]]
        :returns: Tuple containing a list of up to 100 video watch ids and
            a continuation token, if more videos are available
        """
        initial_data = json.loads(raw_json)
        try:
            # this is the json tree structure, if the json was extracted from
            # html
            important_content = initial_data["contents"][
                "twoColumnBrowseResultsRenderer"
            ]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"][
                "contents"
            ][
                0
            ][
                "itemSectionRenderer"
            ][
                "contents"
            ][
                0
            ][
                "playlistVideoListRenderer"
            ]
        except (KeyError, IndexError, TypeError):
            try:
                # this is the json tree structure, if the json was directly sent
                # by the server in a continuation response
                important_content = initial_data[1]["response"][
                    "continuationContents"
                ]["playlistVideoListContinuation"]
            except (KeyError, IndexError, TypeError) as p:
                print(p)
                return [], None
        videos = important_content["contents"]
        try:
            continuation = important_content["continuations"][0][
                "nextContinuationData"
            ]["continuation"]
        except (KeyError, IndexError):
            # if there is an error, no continuation is available
            continuation = None

        # remove duplicates
        return (
            uniqueify(
                list(
                    # only extract the video ids from the video data
                    map(
                        lambda x: (
                            f"/watch?v="
                            f"{x['playlistVideoRenderer']['videoId']}"
                        ),
                        videos
                    )
                ),
            ),
            continuation,
        )

    def trimmed(self, video_id: str) -> Iterable[str]:
        """Retrieve a list of YouTube video URLs trimmed at the given video ID

        i.e. if the playlist has video IDs 1,2,3,4 calling trimmed(3) returns
        [1,2]
        :type video_id: str
            video ID to trim the returned list of playlist URLs at
        :rtype: List[str]
        :returns:
            List of video URLs from the playlist trimmed at the given ID
        """
        for page in self._paginate(until_watch_id=video_id):
            yield from (self._video_url(watch_path) for watch_path in page)

    @property  # type: ignore
    @cache
    def video_urls(self) -> List[str]:
        """Complete links of all the videos in playlist

        :rtype: List[str]
        :returns: List of video URLs
        """
        return [
            self._video_url(video)
            for page in list(self._paginate())
            for video in page
        ]

    @property
    def videos(self) -> Iterable[YouTube]:
        """Yields YouTube objects of videos in this playlist

        :Yields: YouTube
        """
        yield from (YouTube(url) for url in self.video_urls)

    def __getitem__(self, i: Union[slice, int]) -> Union[str, List[str]]:
        return self.video_urls[i]

    def __len__(self) -> int:
        return len(self.video_urls)

    def __repr__(self) -> str:
        return f"{self.video_urls}"

    @deprecated(
        "This call is unnecessary, you can directly access .video_urls or "
        ".videos"
    )
    def populate_video_urls(self) -> List[str]:  # pragma: no cover
        """Complete links of all the videos in playlist

        :rtype: List[str]
        :returns: List of video URLs
        """
        return self.video_urls

    @deprecated("This function will be removed in the future.")
    def _path_num_prefix_generator(self, reverse=False):  # pragma: no cover
        """Generate number prefixes for the items in the playlist.

        If the number of digits required to name a file,is less than is
        required to name the last file,it prepends 0s.
        So if you have a playlist of 100 videos it will number them like:
        001, 002, 003 ect, up to 100.
        It also adds a space after the number.
        :return: prefix string generator : generator
        """
        digits = len(str(len(self.video_urls)))
        if reverse:
            start, stop, step = (len(self.video_urls), 0, -1)
        else:
            start, stop, step = (1, len(self.video_urls) + 1, 1)
        return (str(i).zfill(digits) for i in range(start, stop, step))

    @deprecated(
        "This function will be removed in the future. Please iterate through "
        ".videos"
    )
    def download_all(
        self,
        download_path: Optional[str] = None,
        prefix_number: bool = True,
        reverse_numbering: bool = False,
        resolution: str = "720p",
    ) -> None:  # pragma: no cover
        """Download all the videos in the the playlist.

        :param download_path:
            (optional) Output path for the playlist If one is not
            specified, defaults to the current working directory.
            This is passed along to the Stream objects.
        :type download_path: str or None
        :param prefix_number:
            (optional) Automatically numbers playlists using the
            _path_num_prefix_generator function.
        :type prefix_number: bool
        :param reverse_numbering:
            (optional) Lets you number playlists in reverse, since some
            playlists are ordered newest -> oldest.
        :type reverse_numbering: bool
        :param resolution:
            Video resolution i.e. "720p", "480p", "360p", "240p", "144p"
        :type resolution: str
        """
        logger.debug("total videos found: %d", len(self.video_urls))
        logger.debug("starting download")

        prefix_gen = self._path_num_prefix_generator(reverse_numbering)

        for link in self.video_urls:
            youtube = YouTube(link)
            dl_stream = (
                youtube.streams.get_by_resolution(resolution=resolution)
                or youtube.streams.get_lowest_resolution()
            )
            assert dl_stream is not None

            logger.debug("download path: %s", download_path)
            if prefix_number:
                prefix = next(prefix_gen)
                logger.debug("file prefix is: %s", prefix)
                dl_stream.download(download_path, filename_prefix=prefix)
            else:
                dl_stream.download(download_path)
            logger.debug("download complete")

    @cache
    def title(self) -> Optional[str]:
        """Extract playlist title

        :return: playlist title (name)
        :rtype: Optional[str]
        """
        pattern = re.compile("<title>(.+?)</title>")
        match = pattern.search(self.html)

        if match is None:
            return None

        return match.group(1).replace("- YouTube", "").strip()

    @staticmethod
    def _video_url(watch_path: str):
        return f"https://www.youtube.com{watch_path}"
