class LyricsNotFound(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super(LyricsNotFound, self).__init__(message)
