from spotdl.metadata import ProviderBase
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError
from spotdl.metadata.providers import ProviderSpotify

class TestProviderSpotify:
    def test_subclass(self):
        assert issubclass(ProviderSpotify, ProviderBase)

    # def test_metadata_not_found_error(self):
    #     provider = ProviderSpotify(spotify=spotify)
    #     with pytest.raises(SpotifyMetadataNotFoundError):
    #         provider.from_query("This track doesn't exist on Spotify.")

