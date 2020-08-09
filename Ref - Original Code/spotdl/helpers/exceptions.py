class PlaylistNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class AlbumNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class ArtistNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class UserNotFoundError(Exception):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class SpotifyPlaylistNotFoundError(PlaylistNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class SpotifyAlbumNotFoundError(AlbumNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class SpotifyArtistNotFoundError(ArtistNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)


class SpotifyUserNotFoundError(UserNotFoundError):
    __module__ = Exception.__module__

    def __init__(self, message=None):
        super().__init__(message)

