# -*- coding: utf-8 -*-
from typing import Any
from typing import Optional

from typing_extensions import Protocol


class OnProgress(Protocol):
    def __call__(
        self, stream: Any, chunk: bytes, bytes_remaining: int
    ) -> None:
        """On download progress callback function.

        :param stream:
            An instance of :class:`Stream <Stream>` being downloaded.
        :type stream:
            :py:class:`pytube.Stream`
        :param bytes chunk:
            Segment of media file binary data, not yet written to disk.
        :param int bytes_remaining:
            How many bytes have been downloaded.

        """
        ...


class OnComplete(Protocol):
    def __call__(self, stream: Any, file_path: Optional[str]) -> None:
        """On download complete handler function.

        :param stream:
            An instance of :class:`Stream <Stream>` being downloaded.
        :type stream:
            :py:class:`pytube.Stream`
        :param file_path:
            The file handle where the media is being written to.
        :type file_path: str

        :rtype: None
        """
        ...


class Monostate:
    def __init__(
        self,
        on_progress: Optional[OnProgress],
        on_complete: Optional[OnComplete],
        title: Optional[str] = None,
        duration: Optional[int] = None,
    ):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.title = title
        self.duration = duration
