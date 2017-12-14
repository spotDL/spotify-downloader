from logzero import setup_logger, LogFormatter


# Create a logger
__log_format = ("%(color)s%(levelname)s:%(end_color)s %(message)s")
__formatter = LogFormatter(fmt=__log_format)
log = setup_logger(formatter=__formatter)
