from spotdl.metadata.exceptions import MetadataNotFoundError
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError
from spotdl.metadata.exceptions import YouTubeMetadataNotFoundError


class TestMetadataNotFoundSubclass:
    def test_metadata_not_found_subclass(self):
        assert issubclass(MetadataNotFoundError, Exception)

    def test_spotify_metadata_not_found(self):
        assert issubclass(SpotifyMetadataNotFoundError, MetadataNotFoundError)

    def test_youtube_metadata_not_found(self):
        assert issubclass(YouTubeMetadataNotFoundError, MetadataNotFoundError)

