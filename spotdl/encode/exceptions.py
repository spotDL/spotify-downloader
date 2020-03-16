class EncoderNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super(EncoderNotFoundError, self).__init__(message)


class FFmpegNotFoundError(EncoderNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super(FFmpegNotFoundError, self).__init__(message)


class AvconvNotFoundError(EncoderNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super(AvconvNotFoundError, self).__init__(message)

