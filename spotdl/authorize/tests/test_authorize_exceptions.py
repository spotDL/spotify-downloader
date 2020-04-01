from spotdl.authorize.exceptions import AuthorizationError
from spotdl.authorize.exceptions import SpotifyAuthorizationError
from spotdl.authorize.exceptions import YouTubeAuthorizationError


class TestEncoderNotFoundSubclass:
    def test_authozation_error_subclass(self):
        assert issubclass(AuthorizationError, Exception)

    def test_spotify_authorization_error_subclass(self):
        assert issubclass(SpotifyAuthorizationError, AuthorizationError)

    def test_youtube_authorization_error_subclass(self):
        assert issubclass(YouTubeAuthorizationError, AuthorizationError)

