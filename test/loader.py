import pafy

from spotdl import youtube_tools
from spotdl import spotify_tools
from spotdl import const
from spotdl import handle
from spotdl import spotdl

import pytest


def load_defaults():
    const.args = handle.get_arguments(raw_args="", to_group=False, to_merge=False)
    const.args.overwrite = "skip"
    const.args.log_level = 10

    spotdl.args = const.args
    spotdl.log = const.logzero.setup_logger(
        formatter=const._formatter, level=const.args.log_level
    )


def match_url_in_search_results(url, raw_song):
    metadata = spotify_tools.generate_metadata(raw_song)
    url_fetcher = youtube_tools.GenerateYouTubeURL(raw_song, metadata)
    video_info = url_fetcher.scrape(bestmatch=False)
    for video in video_info:
        if video["link"] in url:
            return video
    assert (False, "Could not match generated YouTube URL from expected YouTube URLs")
