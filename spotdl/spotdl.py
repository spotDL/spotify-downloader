#!/usr/bin/env python3

import sys
import platform
import pprint
import logzero
from logzero import logger as log

from spotdl import __version__
from spotdl import const
from spotdl import handle
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import downloader


def debug_sys_info():
    log.debug("Python version: {}".format(sys.version))
    log.debug("Platform: {}".format(platform.platform()))
    log.debug(pprint.pformat(const.args.__dict__))


