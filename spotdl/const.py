import logzero

_log_format = "%(color)s%(levelname)s:%(end_color)s %(message)s"
_formatter = logzero.LogFormatter(fmt=_log_format)
_log_level = 0

# Set up a temporary logger with default log level so that
# it can be used before log level argument is determined
logzero.setup_default_logger(formatter=_formatter, level=_log_level)

# Options
# Initialize an empty object which can be assigned attributes
# (useful when using spotdl as a library)
args = type("", (), {})()

