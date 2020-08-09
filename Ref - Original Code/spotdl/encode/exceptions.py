class EncoderNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class FFmpegNotFoundError(EncoderNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)

