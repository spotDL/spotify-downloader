class MetadataNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class SpotifyMetadataNotFoundError(MetadataNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class YouTubeMetadataNotFoundError(MetadataNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)

