import logzero
import logging

_LOG_LEVELS_STR = ['INFO', 'WARNING', 'ERROR', 'DEBUG']

def log_leveller(log_level_str):
    loggin_levels = [logging.INFO, logging.WARNING, logging.ERROR, logging.DEBUG]
    log_level_str_index = _LOG_LEVELS_STR.index(log_level_str)
    loggin_level = loggin_levels[log_level_str_index]
    return loggin_level


log_format = ("%(color)s%(levelname)s:%(end_color)s %(message)s")
formatter = logzero.LogFormatter(fmt=log_format)
# create a default logger
log = logzero.setup_logger(formatter=formatter)
