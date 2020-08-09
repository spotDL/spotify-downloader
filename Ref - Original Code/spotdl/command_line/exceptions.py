class NoYouTubeVideoFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class NoYouTubeVideoMatchError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class ArgumentError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)

