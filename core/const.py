import logzero

_log_format = ("%(color)s%(levelname)s:%(end_color)s %(message)s")
formatter = logzero.LogFormatter(fmt=_log_format)

# options
log = logzero.setup_logger(formatter=formatter)
args = None
