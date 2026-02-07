"""Tests for MatchService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.core.services.match import (
    Match,
    MatchService,
    MatchServiceError,
    NoMatchFoundError,
    get_match_service,
)
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song


@pytest.fixture
def match_service() -> MatchService:
    """Create a match service instance for testing with all providers enabled."""
    # Enable all providers for comprehensive testing
    from spotdl.core.providers_config import ProviderPreference

    audio_prefs: list[ProviderPreference] = [
        {"id": "youtube_music", "enabled": True},
        {"id": "youtube", "enabled": True},
        {"id": "soundcloud", "enabled": True},
        {"id": "bandcamp", "enabled": True},
        {"id": "piped", "enabled": True},
    ]
    return MatchService(audio_preferences=audio_prefs)


@pytest.fixture
def mock_song() -> Song:
    """Create a mock song for testing."""
    return Song(
        name="Test Song",
        artists=["Artist 1", "Artist 2"],
        artist="Artist 1",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="abc123",
        url="https://open.spotify.com/track/abc123",
        album_name="Test Album",
        isrc="USABC1234567",
    )


@pytest.fixture
def mock_result() -> Result:
    """Create a mock result for testing."""
    return Result(
        name="Test Song",
        artists=["Artist 1"],
        artist="Artist 1",
        duration=200,
        platform=TargetPlatform.YOUTUBE,
        platform_id="xyz789",
        url="https://www.youtube.com/watch?v=xyz789",
    )


class TestMatch:
    """Tests for Match dataclass."""

    def test_match_properties(self, mock_song: Song, mock_result: Result) -> None:
        """Test Match properties."""
        match = Match(
            source_song=mock_song,
            target_result=mock_result,
            score=85.0,
            match_type="system",
            confidence=0.85,
        )

        assert match.source_url == mock_song.url
        assert match.target_url == mock_result.url
        assert match.target_platform == TargetPlatform.YOUTUBE
        assert match.score == 85.0
        assert match.match_type == "system"
        assert match.confidence == 0.85

    def test_match_user_type(self, mock_song: Song, mock_result: Result) -> None:
        """Test Match with user type."""
        match = Match(
            source_song=mock_song,
            target_result=mock_result,
            score=100.0,
            match_type="user",
            confidence=1.0,
        )

        assert match.match_type == "user"


class TestMatchServiceInit:
    """Tests for MatchService initialization."""

    def test_init_creates_providers(self, match_service: MatchService) -> None:
        """Test that init creates all target providers."""
        assert match_service.get_provider(TargetPlatform.YOUTUBE) is not None
        assert match_service.get_provider(TargetPlatform.YOUTUBE_MUSIC) is not None
        assert match_service.get_provider(TargetPlatform.SOUNDCLOUD) is not None
        assert match_service.get_provider(TargetPlatform.BANDCAMP) is not None
        assert match_service.get_provider(TargetPlatform.PIPED) is not None

    def test_supported_platforms(self, match_service: MatchService) -> None:
        """Test supported_platforms property."""
        platforms = match_service.supported_platforms

        assert TargetPlatform.YOUTUBE in platforms
        assert TargetPlatform.YOUTUBE_MUSIC in platforms
        assert len(platforms) == 5


class TestMatchServiceErrors:
    """Tests for MatchService error handling."""

    def test_match_service_error(self) -> None:
        """Test MatchServiceError."""
        error = MatchServiceError("Test error")
        assert str(error) == "Test error"

    def test_no_match_found_error(self) -> None:
        """Test NoMatchFoundError inherits from MatchServiceError."""
        error = NoMatchFoundError("No match")
        assert isinstance(error, MatchServiceError)
        assert str(error) == "No match"


class TestMatchServiceFindMatches:
    """Tests for MatchService find_matches."""

    @pytest.mark.asyncio
    async def test_find_matches_returns_list(self, match_service: MatchService, mock_song: Song) -> None:
        """Test find_matches returns a list."""
        # This will return empty list since no real search is performed
        # but verifies the method works
        with patch.object(match_service._providers[TargetPlatform.YOUTUBE], 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            matches = await match_service.find_matches(mock_song, target_platforms=[TargetPlatform.YOUTUBE])
            assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_find_matches_specific_platforms(self, match_service: MatchService, mock_song: Song) -> None:
        """Test find_matches with specific platforms."""
        with patch.object(match_service._providers[TargetPlatform.YOUTUBE], 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            matches = await match_service.find_matches(
                mock_song,
                target_platforms=[TargetPlatform.YOUTUBE],
                limit=5,
            )
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_best_match_returns_none_when_empty(self, match_service: MatchService, mock_song: Song) -> None:
        """Test find_best_match returns None when no matches."""
        with patch.object(match_service, 'find_matches', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            result = await match_service.find_best_match(mock_song)
            assert result is None

    @pytest.mark.asyncio
    async def test_find_match_on_platform(self, match_service: MatchService, mock_song: Song) -> None:
        """Test find_match_on_platform."""
        with patch.object(match_service, 'find_matches', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            await match_service.find_match_on_platform(mock_song, TargetPlatform.YOUTUBE)
            mock_find.assert_called_once_with(
                mock_song,
                target_platforms=[TargetPlatform.YOUTUBE],
                limit=5,
            )


class TestMatchServiceFindMatchesWithResults:
    """Tests for MatchService find_matches with actual results."""

    @pytest.fixture
    def mock_results(self) -> list[Result]:
        """Create mock results for testing."""
        return [
            Result(
                name="Test Song - Official Video",
                artists=["Artist 1"],
                artist="Artist 1",
                duration=200,
                platform=TargetPlatform.YOUTUBE,
                platform_id="vid1",
                url="https://www.youtube.com/watch?v=vid1",
            ),
            Result(
                name="Test Song (Lyric Video)",
                artists=["Artist 1"],
                artist="Artist 1",
                duration=198,
                platform=TargetPlatform.YOUTUBE,
                platform_id="vid2",
                url="https://www.youtube.com/watch?v=vid2",
            ),
        ]

    @pytest.mark.asyncio
    async def test_find_matches_with_results(
        self,
        match_service: MatchService,
        mock_song: Song,
        mock_results: list[Result],
    ) -> None:
        """Test find_matches returns Match objects when results found."""
        with patch.object(
            match_service._providers[TargetPlatform.YOUTUBE],
            "search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_results

            matches = await match_service.find_matches(
                mock_song,
                target_platforms=[TargetPlatform.YOUTUBE],
                limit=5,
            )

            assert len(matches) > 0
            assert all(isinstance(m, Match) for m in matches)
            assert all(m.source_song == mock_song for m in matches)
            # Matches should be sorted by score
            scores = [m.score for m in matches]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_find_matches_default_platforms(
        self,
        match_service: MatchService,
        mock_song: Song,
    ) -> None:
        """Test find_matches uses all platforms by default."""
        # Patch all providers to return empty to avoid network calls
        for platform, provider in match_service._providers.items():
            with patch.object(provider, "search", new_callable=AsyncMock) as mock:
                mock.return_value = []

        matches = await match_service.find_matches(mock_song)
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_find_matches_handles_search_error(
        self,
        match_service: MatchService,
        mock_song: Song,
    ) -> None:
        """Test find_matches handles SearchError gracefully."""
        from spotdl.providers.targets import SearchError

        with patch.object(
            match_service._providers[TargetPlatform.YOUTUBE],
            "search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = SearchError("Search failed")

            matches = await match_service.find_matches(
                mock_song,
                target_platforms=[TargetPlatform.YOUTUBE],
            )

            # Should return empty list, not raise
            assert matches == []

    @pytest.mark.asyncio
    async def test_find_matches_skips_unknown_platform(
        self,
        match_service: MatchService,
        mock_song: Song,
    ) -> None:
        """Test find_matches skips platforms without providers."""
        # Clear providers to simulate missing platform
        original_providers = match_service._providers.copy()
        match_service._providers = {}

        matches = await match_service.find_matches(
            mock_song,
            target_platforms=[TargetPlatform.YOUTUBE],
        )

        assert matches == []

        # Restore providers
        match_service._providers = original_providers

    @pytest.mark.asyncio
    async def test_find_best_match_returns_match(
        self,
        match_service: MatchService,
        mock_song: Song,
        mock_results: list[Result],
    ) -> None:
        """Test find_best_match returns best Match when results found."""
        with patch.object(
            match_service._providers[TargetPlatform.YOUTUBE],
            "search",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_results

            best = await match_service.find_best_match(
                mock_song,
                target_platforms=[TargetPlatform.YOUTUBE],
            )

            assert best is not None
            assert isinstance(best, Match)


class TestMatchServiceISRC:
    """Tests for MatchService ISRC search."""

    @pytest.mark.asyncio
    async def test_search_by_isrc_no_isrc(self, match_service: MatchService, mock_song: Song) -> None:
        """Test search_by_isrc returns None when song has no ISRC."""
        mock_song.isrc = None
        result = await match_service.search_by_isrc(mock_song)
        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_isrc_no_provider(self, match_service: MatchService, mock_song: Song) -> None:
        """Test search_by_isrc returns None when provider not found."""
        # Clear providers
        original_providers = match_service._providers.copy()
        match_service._providers = {}

        result = await match_service.search_by_isrc(mock_song)
        assert result is None

        # Restore
        match_service._providers = original_providers

    @pytest.mark.asyncio
    async def test_search_by_isrc_provider_no_method(self, match_service: MatchService, mock_song: Song) -> None:
        """Test search_by_isrc returns None when provider lacks method."""
        # Create a provider without search_by_isrc
        mock_provider = MagicMock()
        del mock_provider.search_by_isrc  # Remove the method

        match_service._providers[TargetPlatform.YOUTUBE_MUSIC] = mock_provider

        result = await match_service.search_by_isrc(mock_song)
        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_isrc_with_result(self, match_service: MatchService, mock_song: Song) -> None:
        """Test search_by_isrc returns Match when result found."""
        mock_result = Result(
            name="Test Song",
            artists=["Artist 1"],
            artist="Artist 1",
            duration=200,
            platform=TargetPlatform.YOUTUBE_MUSIC,
            platform_id="isrc_vid",
            url="https://music.youtube.com/watch?v=isrc_vid",
            isrc_search=True,
        )

        with patch.object(
            match_service._providers[TargetPlatform.YOUTUBE_MUSIC],
            "search_by_isrc",
            new_callable=AsyncMock,
        ) as mock_isrc:
            mock_isrc.return_value = mock_result

            result = await match_service.search_by_isrc(mock_song)

            assert result is not None
            assert isinstance(result, Match)
            assert result.source_song == mock_song

    @pytest.mark.asyncio
    async def test_search_by_isrc_no_result(self, match_service: MatchService, mock_song: Song) -> None:
        """Test search_by_isrc returns None when no result found."""
        with patch.object(
            match_service._providers[TargetPlatform.YOUTUBE_MUSIC],
            "search_by_isrc",
            new_callable=AsyncMock,
        ) as mock_isrc:
            mock_isrc.return_value = None

            result = await match_service.search_by_isrc(mock_song)
            assert result is None

    @pytest.mark.asyncio
    async def test_search_by_isrc_handles_search_error(self, match_service: MatchService, mock_song: Song) -> None:
        """Test search_by_isrc handles SearchError gracefully."""
        from spotdl.providers.targets import SearchError

        with patch.object(
            match_service._providers[TargetPlatform.YOUTUBE_MUSIC],
            "search_by_isrc",
            new_callable=AsyncMock,
        ) as mock_isrc:
            mock_isrc.side_effect = SearchError("ISRC search failed")

            result = await match_service.search_by_isrc(mock_song)
            assert result is None


class TestMatchServiceClose:
    """Tests for MatchService cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, match_service: MatchService) -> None:
        """Test close method closes all providers."""
        await match_service.close()
        # Should not raise


class TestGetMatchService:
    """Tests for get_match_service function."""

    def test_get_match_service_returns_instance(self) -> None:
        """Test get_match_service returns a MatchService."""
        import spotdl.core.services.match as match_module
        match_module._match_service = None

        service = get_match_service()
        assert isinstance(service, MatchService)

    def test_get_match_service_singleton(self) -> None:
        """Test get_match_service returns same instance."""
        import spotdl.core.services.match as match_module
        match_module._match_service = None

        service1 = get_match_service()
        service2 = get_match_service()
        assert service1 is service2
