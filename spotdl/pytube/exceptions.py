# -*- coding: utf-8 -*-
"""Library specific exception definitions."""
from typing import Pattern
from typing import Union


class PytubeError(Exception):
    """Base pytube exception that all others inherent.

    This is done to not pollute the built-in exceptions, which *could* result
    in unintended errors being unexpectedly and incorrectly handled within
    implementers code.
    """


class ExtractError(PytubeError):
    """Data extraction based exception."""


class RegexMatchError(ExtractError):
    """Regex pattern did not return any matches."""

    def __init__(self, caller: str, pattern: Union[str, Pattern]):
        """
        :param str caller:
            Calling function
        :param str pattern:
            Pattern that failed to match
        """
        super().__init__(f"{caller}: could not find match for {pattern}")
        self.caller = caller
        self.pattern = pattern


class LiveStreamError(ExtractError):
    """Video is a live stream."""

    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        super().__init__(f"{video_id} is streaming live and cannot be loaded")

        self.video_id = video_id


class VideoUnavailable(PytubeError):
    """Video is unavailable."""

    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        super().__init__(f"{video_id} is unavailable")

        self.video_id = video_id


class HTMLParseError(PytubeError):
    """HTML could not be parsed"""
