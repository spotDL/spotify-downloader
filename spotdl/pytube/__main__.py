# -*- coding: utf-8 -*-
"""
This module implements the core developer interface for pytube.

The problem domain of the :class:`YouTube <YouTube> class focuses almost
exclusively on the developer interface. Pytube offloads the heavy lifting to
smaller peripheral modules and functions.

"""
import json
import logging
from html import unescape
from typing import Dict
from typing import List
from typing import Optional
from urllib.parse import parse_qsl

from pytube import Caption
from pytube import CaptionQuery
from pytube import extract
from pytube import request
from pytube import Stream
from pytube import StreamQuery
from pytube.exceptions import VideoUnavailable
from pytube.extract import apply_descrambler
from pytube.extract import apply_signature
from pytube.extract import get_ytplayer_config
from pytube.helpers import install_proxy
from pytube.monostate import Monostate
from pytube.monostate import OnComplete
from pytube.monostate import OnProgress

logger = logging.getLogger(__name__)


class YouTube:
    """Core developer interface for pytube."""

    def __init__(
        self,
        url: str,
        defer_prefetch_init: bool = False,
        on_progress_callback: Optional[OnProgress] = None,
        on_complete_callback: Optional[OnComplete] = None,
        proxies: Dict[str, str] = None,
    ):
        """Construct a :class:`YouTube <YouTube>`.

        :param str url:
            A valid YouTube watch URL.
        :param bool defer_prefetch_init:
            Defers executing any network requests.
        :param func on_progress_callback:
            (Optional) User defined callback function for stream download
            progress events.
        :param func on_complete_callback:
            (Optional) User defined callback function for stream download
            complete events.

        """
        self.js: Optional[str] = None  # js fetched by js_url
        self.js_url: Optional[
            str
        ] = None  # the url to the js, parsed from watch html

        # note: vid_info may eventually be removed. It sounds like it once had
        # additional formats, but that doesn't appear to still be the case.

        # the url to vid info, parsed from watch html
        self.vid_info_url: Optional[str] = None
        self.vid_info_raw: Optional[
            str
        ] = None  # content fetched by vid_info_url
        self.vid_info: Optional[Dict] = None  # parsed content of vid_info_raw

        self.watch_html: Optional[
            str
        ] = None  # the html of /watch?v=<video_id>
        self.embed_html: Optional[str] = None
        self.player_config_args: Dict = {}  # inline js in the html containing
        self.player_response: Dict = {}
        # streams
        self.age_restricted: Optional[bool] = None

        self.fmt_streams: List[Stream] = []

        # video_id part of /watch?v=<video_id>
        self.video_id = extract.video_id(url)

        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"

        # Shared between all instances of `Stream` (Borg pattern).
        self.stream_monostate = Monostate(
            on_progress=on_progress_callback, on_complete=on_complete_callback
        )

        if proxies:
            install_proxy(proxies)

        if not defer_prefetch_init:
            self.prefetch()
            self.descramble()

    def descramble(self) -> None:
        """Descramble the stream data and build Stream instances.

        The initialization process takes advantage of Python's
        "call-by-reference evaluation," which allows dictionary transforms to
        be applied in-place, instead of holding references to mutations at each
        interstitial step.

        :rtype: None

        """
        logger.info("init started")

        self.vid_info = dict(parse_qsl(self.vid_info_raw))
        if self.age_restricted:
            self.player_config_args = self.vid_info
        else:
            assert self.watch_html is not None
            self.player_config_args = get_ytplayer_config(self.watch_html)[
                "args"
            ]

            # Fix for KeyError: 'title' issue #434
            if "title" not in self.player_config_args:  # type: ignore
                i_start = self.watch_html.lower().index("<title>") + len(
                    "<title>"
                )
                i_end = self.watch_html.lower().index("</title>")
                title = self.watch_html[i_start:i_end].strip()
                index = title.lower().rfind(" - youtube")
                title = title[:index] if index > 0 else title
                self.player_config_args["title"] = unescape(title)

        # https://github.com/nficano/pytube/issues/165
        stream_maps = ["url_encoded_fmt_stream_map"]
        if "adaptive_fmts" in self.player_config_args:
            stream_maps.append("adaptive_fmts")

        # unscramble the progressive and adaptive stream manifests.
        for fmt in stream_maps:
            if not self.age_restricted and fmt in self.vid_info:
                apply_descrambler(self.vid_info, fmt)
            apply_descrambler(self.player_config_args, fmt)

            if not self.js:
                if not self.embed_html:
                    self.embed_html = request.get(url=self.embed_url)
                self.js_url = extract.js_url(self.embed_html)
                self.js = request.get(self.js_url)

            apply_signature(self.player_config_args, fmt, self.js)

            # build instances of :class:`Stream <Stream>`
            self.initialize_stream_objects(fmt)

        # load the player_response object (contains subtitle information)
        self.player_response = json.loads(
            self.player_config_args["player_response"]
        )
        del self.player_config_args["player_response"]
        self.stream_monostate.title = self.title
        self.stream_monostate.duration = self.length

        logger.info("init finished successfully")

    def prefetch(self) -> None:
        """Eagerly download all necessary data.

        Eagerly executes all necessary network requests so all other
        operations don't does need to make calls outside of the interpreter
        which blocks for long periods of time.

        :rtype: None
        """
        self.watch_html = request.get(url=self.watch_url)
        if self.watch_html is None:
            raise VideoUnavailable(video_id=self.video_id)
        self.age_restricted = extract.is_age_restricted(self.watch_html)

        if (
            not self.age_restricted
            and "This video is private" in self.watch_html
        ):
            raise VideoUnavailable(video_id=self.video_id)

        if self.age_restricted:
            if not self.embed_html:
                self.embed_html = request.get(url=self.embed_url)
            self.vid_info_url = extract.video_info_url_age_restricted(
                self.video_id, self.watch_url
            )
        else:
            self.vid_info_url = extract.video_info_url(
                video_id=self.video_id, watch_url=self.watch_url
            )

        self.vid_info_raw = request.get(self.vid_info_url)
        if not self.age_restricted:
            self.js_url = extract.js_url(self.watch_html)
            self.js = request.get(self.js_url)

    def initialize_stream_objects(self, fmt: str) -> None:
        """Convert manifest data to instances of :class:`Stream <Stream>`.

        Take the unscrambled stream data and uses it to initialize
        instances of :class:`Stream <Stream>` for each media stream.

        :param str fmt:
            Key in stream manifest (``ytplayer_config``) containing progressive
            download or adaptive streams (e.g.: ``url_encoded_fmt_stream_map``
            or ``adaptive_fmts``).

        :rtype: None

        """
        stream_manifest = self.player_config_args[fmt]
        for stream in stream_manifest:
            video = Stream(
                stream=stream,
                player_config_args=self.player_config_args,
                monostate=self.stream_monostate,
            )
            self.fmt_streams.append(video)

    @property
    def caption_tracks(self) -> List[Caption]:
        """Get a list of :class:`Caption <Caption>`.

        :rtype: List[Caption]
        """
        raw_tracks = (
            self.player_response.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        return [Caption(track) for track in raw_tracks]

    @property
    def captions(self) -> CaptionQuery:
        """Interface to query caption tracks.

        :rtype: :class:`CaptionQuery <CaptionQuery>`.
        """
        return CaptionQuery(self.caption_tracks)

    @property
    def streams(self) -> StreamQuery:
        """Interface to query both adaptive (DASH) and progressive streams.

        :rtype: :class:`StreamQuery <StreamQuery>`.
        """
        return StreamQuery(self.fmt_streams)

    @property
    def thumbnail_url(self) -> str:
        """Get the thumbnail url image.

        :rtype: str

        """
        thumbnail_details = (
            self.player_response.get("videoDetails", {})
            .get("thumbnail", {})
            .get("thumbnails")
        )
        if thumbnail_details:
            thumbnail_details = thumbnail_details[-1]  # last item has max size
            return thumbnail_details["url"]

        return f"https://img.youtube.com/vi/{self.video_id}/maxresdefault.jpg"

    @property
    def title(self) -> str:
        """Get the video title.

        :rtype: str

        """
        return self.player_config_args.get("title") or (
            self.player_response.get("videoDetails", {}).get("title")
        )

    @property
    def description(self) -> str:
        """Get the video description.

        :rtype: str

        """
        return self.player_response.get("videoDetails", {}).get(
            "shortDescription"
        )

    @property
    def rating(self) -> float:
        """Get the video average rating.

        :rtype: float

        """
        return self.player_response.get("videoDetails", {}).get(
            "averageRating"
        )

    @property
    def length(self) -> int:
        """Get the video length in seconds.

        :rtype: str

        """
        return int(
            self.player_config_args.get("length_seconds")
            or (
                self.player_response.get("videoDetails", {}).get(
                    "lengthSeconds"
                )
            )
        )

    @property
    def views(self) -> int:
        """Get the number of the times the video has been viewed.

        :rtype: str

        """
        return int(
            self.player_response.get("videoDetails", {}).get("viewCount")
        )

    @property
    def author(self) -> str:
        """Get the video author.
        :rtype: str
        """
        return self.player_response.get("videoDetails", {}).get(
            "author", "unknown"
        )

    def register_on_progress_callback(self, func: OnProgress):
        """Register a download progress callback function post initialization.

        :param callable func:
            A callback function that takes ``stream``, ``chunk``,
             and ``bytes_remaining`` as parameters.

        :rtype: None

        """
        self.stream_monostate.on_progress = func

    def register_on_complete_callback(self, func: OnComplete):
        """Register a download complete callback function post initialization.

        :param callable func:
            A callback function that takes ``stream`` and  ``file_path``.

        :rtype: None

        """
        self.stream_monostate.on_complete = func
