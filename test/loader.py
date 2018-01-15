from core import const
from core import handle
import spotdl


def load_defaults():
    const.args = handle.get_arguments(to_group=False, raw_args='')
    const.args.folder = 'test'
    const.args.overwrite = 'skip'
    const.args.log_level = handle.logging.DEBUG

    spotdl.args = const.args
    spotdl.log = const.logzero.setup_logger(formatter=const.formatter,
                                      level=const.args.log_level)
