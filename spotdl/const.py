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

# Apple has specific tags - see mutagen docs -
# http://mutagen.readthedocs.io/en/latest/api/mp4.html
M4A_TAG_PRESET = {
    "album": "\xa9alb",
    "artist": "\xa9ART",
    "date": "\xa9day",
    "title": "\xa9nam",
    "year": "\xa9day",
    "originaldate": "purd",
    "comment": "\xa9cmt",
    "group": "\xa9grp",
    "writer": "\xa9wrt",
    "genre": "\xa9gen",
    "tracknumber": "trkn",
    "albumartist": "aART",
    "discnumber": "disk",
    "cpil": "cpil",
    "albumart": "covr",
    "copyright": "cprt",
    "tempo": "tmpo",
    "lyrics": "\xa9lyr",
    "comment": "\xa9cmt",
}

TAG_PRESET = {}
for key in M4A_TAG_PRESET.keys():
    TAG_PRESET[key] = key
