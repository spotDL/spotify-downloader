from spotdl import const
from spotdl import handle
from spotdl import spotdl
import urllib

import pytest


def load_defaults():
    const.args = handle.get_arguments(raw_args="", to_group=False, to_merge=False)
    const.args.overwrite = "skip"

    spotdl.args = const.args
    spotdl.log = const.logzero.setup_logger(
        formatter=const._formatter, level=const.args.log_level
    )


# GIST_URL is the monkeypatched version of: https://www.youtube.com/results?search_query=janji+-+heroes
# so that we get same results even if YouTube changes the list/order of videos on their page.
GIST_URL = "https://gist.githubusercontent.com/ritiek/e731338e9810e31c2f00f13c249a45f5/raw/c11a27f3b5d11a8d082976f1cdd237bd605ec2c2/search_results.html"

def monkeypatch_youtube_search_page(*args, **kwargs):
    fake_urlopen = urllib.request.urlopen(GIST_URL)
    return fake_urlopen

