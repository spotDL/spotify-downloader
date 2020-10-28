# -*- coding: utf-8 -*-
"""This module provides a query interface for media streams and captions."""
from collections.abc import Mapping
from collections.abc import Sequence
from typing import Callable
from typing import List
from typing import Optional
from typing import Union

from pytube import Caption
from pytube import Stream
from pytube.helpers import deprecated


class StreamQuery(Sequence):
    """Interface for querying the available media streams."""

    def __init__(self, fmt_streams):
        """Construct a :class:`StreamQuery <StreamQuery>`.

        param list fmt_streams:
            list of :class:`Stream <Stream>` instances.
        """
        self.fmt_streams = fmt_streams
        self.itag_index = {int(s.itag): s for s in fmt_streams}

    def filter(
        self,
        fps=None,
        res=None,
        resolution=None,
        mime_type=None,
        type=None,
        subtype=None,
        file_extension=None,
        abr=None,
        bitrate=None,
        video_codec=None,
        audio_codec=None,
        only_audio=None,
        only_video=None,
        progressive=None,
        adaptive=None,
        is_dash=None,
        custom_filter_functions=None,
    ):
        """Apply the given filtering criterion.

        :param fps:
            (optional) The frames per second.
        :type fps:
            int or None

        :param resolution:
            (optional) Alias to ``res``.
        :type res:
            str or None

        :param res:
            (optional) The video resolution.
        :type resolution:
            str or None

        :param mime_type:
            (optional) Two-part identifier for file formats and format contents
            composed of a "type", a "subtype".
        :type mime_type:
            str or None

        :param type:
            (optional) Type part of the ``mime_type`` (e.g.: audio, video).
        :type type:
            str or None

        :param subtype:
            (optional) Sub-type part of the ``mime_type`` (e.g.: mp4, mov).
        :type subtype:
            str or None

        :param file_extension:
            (optional) Alias to ``sub_type``.
        :type file_extension:
            str or None

        :param abr:
            (optional) Average bitrate (ABR) refers to the average amount of
            data transferred per unit of time (e.g.: 64kbps, 192kbps).
        :type abr:
            str or None

        :param bitrate:
            (optional) Alias to ``abr``.
        :type bitrate:
            str or None

        :param video_codec:
            (optional) Video compression format.
        :type video_codec:
            str or None

        :param audio_codec:
            (optional) Audio compression format.
        :type audio_codec:
            str or None

        :param bool progressive:
            Excludes adaptive streams (one file contains both audio and video
            tracks).

        :param bool adaptive:
            Excludes progressive streams (audio and video are on separate
            tracks).

        :param bool is_dash:
            Include/exclude dash streams.

        :param bool only_audio:
            Excludes streams with video tracks.

        :param bool only_video:
            Excludes streams with audio tracks.

        :param custom_filter_functions:
            (optional) Interface for defining complex filters without
            subclassing.
        :type custom_filter_functions:
            list or None

        """
        filters = []
        if res or resolution:
            filters.append(lambda s: s.resolution == (res or resolution))

        if fps:
            filters.append(lambda s: s.fps == fps)

        if mime_type:
            filters.append(lambda s: s.mime_type == mime_type)

        if type:
            filters.append(lambda s: s.type == type)

        if subtype or file_extension:
            filters.append(lambda s: s.subtype == (subtype or file_extension))

        if abr or bitrate:
            filters.append(lambda s: s.abr == (abr or bitrate))

        if video_codec:
            filters.append(lambda s: s.video_codec == video_codec)

        if audio_codec:
            filters.append(lambda s: s.audio_codec == audio_codec)

        if only_audio:
            filters.append(
                lambda s: (
                    s.includes_audio_track and not s.includes_video_track
                ),
            )

        if only_video:
            filters.append(
                lambda s: (
                    s.includes_video_track and not s.includes_audio_track
                ),
            )

        if progressive:
            filters.append(lambda s: s.is_progressive)

        if adaptive:
            filters.append(lambda s: s.is_adaptive)

        if custom_filter_functions:
            filters.extend(custom_filter_functions)

        if is_dash is not None:
            filters.append(lambda s: s.is_dash == is_dash)

        return self._filter(filters)

    def _filter(self, filters: List[Callable]) -> "StreamQuery":
        fmt_streams = self.fmt_streams
        for filter_lambda in filters:
            fmt_streams = filter(filter_lambda, fmt_streams)
        return StreamQuery(list(fmt_streams))

    def order_by(self, attribute_name: str) -> "StreamQuery":
        """Apply a sort order. Filters out stream the do not have the attribute.

        :param str attribute_name:
            The name of the attribute to sort by.
        """
        has_attribute = [
            s
            for s in self.fmt_streams
            if getattr(s, attribute_name) is not None
        ]
        # Check that the attributes have string values.
        if has_attribute and isinstance(
            getattr(has_attribute[0], attribute_name), str
        ):
            # Try to return a StreamQuery sorted by the integer representations
            # of the values.
            try:
                return StreamQuery(
                    sorted(
                        has_attribute,
                        key=lambda s: int(
                            "".join(
                                filter(str.isdigit, getattr(s, attribute_name))
                            )
                        ),  # type: ignore  # noqa: E501
                    )
                )
            except ValueError:
                pass

        return StreamQuery(
            sorted(has_attribute, key=lambda s: getattr(s, attribute_name))
        )

    def desc(self) -> "StreamQuery":
        """Sort streams in descending order.

        :rtype: :class:`StreamQuery <StreamQuery>`

        """
        return StreamQuery(self.fmt_streams[::-1])

    def asc(self) -> "StreamQuery":
        """Sort streams in ascending order.

        :rtype: :class:`StreamQuery <StreamQuery>`

        """
        return self

    def get_by_itag(self, itag: int) -> Optional[Stream]:
        """Get the corresponding :class:`Stream <Stream>` for a given itag.

        :param int itag:
            YouTube format identifier code.
        :rtype: :class:`Stream <Stream>` or None
        :returns:
            The :class:`Stream <Stream>` matching the given itag or None if
            not found.

        """
        return self.itag_index.get(int(itag))

    def get_by_resolution(self, resolution: str) -> Optional[Stream]:
        """Get the corresponding :class:`Stream <Stream>` for a given resolution.

        Stream must be a progressive mp4.

        :param str resolution:
            Video resolution i.e. "720p", "480p", "360p", "240p", "144p"
        :rtype: :class:`Stream <Stream>` or None
        :returns:
            The :class:`Stream <Stream>` matching the given itag or None if
            not found.

        """
        return self.filter(
            progressive=True, subtype="mp4", resolution=resolution
        ).first()

    def get_lowest_resolution(self) -> Optional[Stream]:
        """Get lowest resolution stream that is a progressive mp4.

        :rtype: :class:`Stream <Stream>` or None
        :returns:
            The :class:`Stream <Stream>` matching the given itag or None if
            not found.

        """
        return (
            self.filter(progressive=True, subtype="mp4")
            .order_by("resolution")
            .first()
        )

    def get_highest_resolution(self) -> Optional[Stream]:
        """Get highest resolution stream that is a progressive video.

        :rtype: :class:`Stream <Stream>` or None
        :returns:
            The :class:`Stream <Stream>` matching the given itag or None if
            not found.

        """
        return self.filter(progressive=True).order_by("resolution").last()

    def get_audio_only(self, subtype: str = "mp4") -> Optional[Stream]:
        """Get highest bitrate audio stream for given codec (defaults to mp4)

        :param str subtype:
            Audio subtype, defaults to mp4
        :rtype: :class:`Stream <Stream>` or None
        :returns:
            The :class:`Stream <Stream>` matching the given itag or None if
            not found.
        """
        return (
            self.filter(only_audio=True, subtype=subtype)
            .order_by("abr")
            .last()
        )

    def otf(self, is_otf: bool = False) -> "StreamQuery":
        """Filter stream by OTF, useful if some streams have 404 URLs

        :param bool is_otf: Set to False to retrieve only non-OTF streams
        :rtype: :class:`StreamQuery <StreamQuery>`
        :returns: A StreamQuery object with otf filtered streams
        """
        return self._filter([lambda s: s.is_otf == is_otf])

    def first(self) -> Optional[Stream]:
        """Get the first :class:`Stream <Stream>` in the results.

        :rtype: :class:`Stream <Stream>` or None
        :returns:
            the first result of this query or None if the result doesn't
            contain any streams.

        """
        try:
            return self.fmt_streams[0]
        except IndexError:
            return None

    def last(self):
        """Get the last :class:`Stream <Stream>` in the results.

        :rtype: :class:`Stream <Stream>` or None
        :returns:
            Return the last result of this query or None if the result
            doesn't contain any streams.

        """
        try:
            return self.fmt_streams[-1]
        except IndexError:
            pass

    @deprecated("Get the size of this list directly using len()")
    def count(self, value: Optional[str] = None) -> int:  # pragma: no cover
        """Get the count of items in the list.

        :rtype: int
        """
        if value:
            return self.fmt_streams.count(value)

        return len(self)

    @deprecated("This object can be treated as a list, all() is useless")
    def all(self) -> List[Stream]:  # pragma: no cover
        """Get all the results represented by this query as a list.

        :rtype: list

        """
        return self.fmt_streams

    def __getitem__(self, i: Union[slice, int]):
        return self.fmt_streams[i]

    def __len__(self) -> int:
        return len(self.fmt_streams)

    def __repr__(self) -> str:
        return f"{self.fmt_streams}"


class CaptionQuery(Mapping):
    """Interface for querying the available captions."""

    def __init__(self, captions: List[Caption]):
        """Construct a :class:`Caption <Caption>`.

        param list captions:
            list of :class:`Caption <Caption>` instances.

        """
        self.lang_code_index = {c.code: c for c in captions}

    @deprecated(
        "This object can be treated as a dictionary, i.e. captions['en']"
    )
    def get_by_language_code(
        self, lang_code: str
    ) -> Optional[Caption]:  # pragma: no cover
        """Get the :class:`Caption <Caption>` for a given ``lang_code``.

        :param str lang_code:
            The code that identifies the caption language.
        :rtype: :class:`Caption <Caption>` or None
        :returns:
            The :class:`Caption <Caption>` matching the given ``lang_code`` or
            None if it does not exist.
        """
        return self.lang_code_index.get(lang_code)

    @deprecated("This object can be treated as a dictionary")
    def all(self) -> List[Caption]:  # pragma: no cover
        """Get all the results represented by this query as a list.

        :rtype: list

        """
        return list(self.lang_code_index.values())

    def __getitem__(self, i: str):
        return self.lang_code_index[i]

    def __len__(self) -> int:
        return len(self.lang_code_index)

    def __iter__(self):
        return iter(self.lang_code_index.values())

    def __repr__(self) -> str:
        return f"{self.lang_code_index}"
