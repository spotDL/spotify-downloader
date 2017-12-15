import logzero
import logging


def log_leveller(log_level_str):
    log_levels_str = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
    loggin_levels = [logging.INFO, logging.WARNING, logging.ERROR, logging.DEBUG]
    log_level_str_index = log_levels_str.index(log_level_str)
    loggin_level = loggin_levels[log_level_str_index]
    return loggin_level


# Create a logger
log_format = ("%(color)s%(levelname)s:%(end_color)s %(message)s")
formatter = logzero.LogFormatter(fmt=log_format)
log = logzero.setup_logger(formatter=formatter, level=logging.INFO)
