from spotdl.authorize.services import AuthorizeSpotify

import pytest

class TestSpotifyAuthorize:
    # TODO: Test these once we a have config.py
    #       storing pre-defined default credentials.
    #
    # We'll use these credentials to create
    # a spotipy object via below tests

    @pytest.mark.xfail
    def test_generate_token(self):
        raise NotImplementedError

    @pytest.mark.xfail
    def test_authorize(self):
        raise NotImplementedError

