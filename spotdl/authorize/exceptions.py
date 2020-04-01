class AuthorizationError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class SpotifyAuthorizationError(AuthorizationError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class YouTubeAuthorizationError(AuthorizationError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)

