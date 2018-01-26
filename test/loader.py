from core import const
from core import handle
import spotdl
import pytest


def load_defaults():
    const.args = handle.get_arguments(raw_args='', to_group=False, to_merge=False)
    const.args.overwrite = 'skip'
    const.args.log_level = 10

    spotdl.args = const.args
    spotdl.log = const.logzero.setup_logger(formatter=const.formatter,
                                      level=const.args.log_level)
