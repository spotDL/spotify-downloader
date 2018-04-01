import logzero

_log_format = ("%(color)s%(levelname)s:%(end_color)s %(message)s")
_formatter = logzero.LogFormatter(fmt=_log_format)

# options
log = logzero.setup_logger(formatter=_formatter)
args = None

# Apple has specific tags - see mutagen docs -
# http://mutagen.readthedocs.io/en/latest/api/mp4.html
M4A_TAG_PRESET = { 'album'        : '\xa9alb',
                   'artist'       : '\xa9ART',
                   'date'         : '\xa9day',
                   'title'        : '\xa9nam',
                   'year'         : '\xa9day',
                   'originaldate' : 'purd',
                   'comment'      : '\xa9cmt',
                   'group'        : '\xa9grp',
                   'writer'       : '\xa9wrt',
                   'genre'        : '\xa9gen',
                   'tracknumber'  : 'trkn',
                   'albumartist'  : 'aART',
                   'discnumber'   : 'disk',
                   'cpil'         : 'cpil',
                   'albumart'     : 'covr',
                   'copyright'    : 'cprt',
                   'tempo'        : 'tmpo',
                   'lyrics'       : '\xa9lyr' }

TAG_PRESET = {}
for key in M4A_TAG_PRESET.keys():
    TAG_PRESET[key] = key
