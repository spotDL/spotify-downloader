"""Match service for finding and managing song matches."""

from __future__ import annotations

from dataclasses import dataclass

from spotdl.core.matching.engine import get_best_matches, order_results
from spotdl.core.provider_preferences import (
    get_enabled_audio_platforms,
)
from spotdl.core.providers_config import ProviderPreference
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Song
from spotdl.providers.targets import (
    BandcampProvider,
    PipedProvider,
    SearchError,
    SoundCloudProvider,
    TargetProvider,
    YouTubeMusicProvider,
    YouTubeProvider,
)


class MatchServiceError(Exception):
    """Base exception for match service errors."""


class NoMatchFoundError(MatchServiceError):
    """Raised when no match is found."""


@dataclass
class Match:
    """Represents a match between a source song and target result."""

    source_song: Song
    target_result: Result
    score: float
    match_type: str = "system"  # 'system' or 'user'
    confidence: float = 0.0

    @property
    def source_url(self) -> str:
        """Get source song URL."""
        return self.source_song.url

    @property
    def target_url(self) -> str:
        """Get target result URL."""
        return self.target_result.url

    @property
    def target_platform(self) -> TargetPlatform:
        """Get target platform."""
        return self.target_result.platform


class MatchService:
    """
    Service for finding matches between songs and audio sources.

    Uses target providers to search for potential matches and
    the matching engine to score and rank results.
    """

    def __init__(
        self,
        audio_preferences: list[ProviderPreference] | None = None,
    ) -> None:
        """
        Initialize the match service.

        Args:
            audio_preferences: User's audio source preferences (ordered list with enabled status).
                             If None, uses default preferences.
        """
        self._providers: dict[TargetPlatform, TargetProvider] = {}
        self._platform_order: list[TargetPlatform] = []
        self._init_providers(audio_preferences)

    def _init_providers(
        self,
        audio_preferences: list[ProviderPreference] | None = None,
    ) -> None:
        """
        Initialize target providers based on user preferences.

        Args:
            audio_preferences: User's audio source preferences
        """
        # Get enabled platforms in user-specified order
        enabled_platforms = get_enabled_audio_platforms(audio_preferences)
        self._platform_order = enabled_platforms

        # Provider factory mapping
        provider_classes: dict[TargetPlatform, type[TargetProvider]] = {
            TargetPlatform.YOUTUBE: YouTubeProvider,
            TargetPlatform.YOUTUBE_MUSIC: YouTubeMusicProvider,
            TargetPlatform.SOUNDCLOUD: SoundCloudProvider,
            TargetPlatform.BANDCAMP: BandcampProvider,
            TargetPlatform.PIPED: PipedProvider,
        }

        # Initialize only enabled providers in the specified order
        for platform in enabled_platforms:
            provider_class = provider_classes.get(platform)
            if provider_class is not None:
                self._providers[platform] = provider_class()

    def get_provider(self, platform: TargetPlatform) -> TargetProvider | None:
        """
        Get the provider for a target platform.

        Args:
            platform: Target platform

        Returns:
            Provider instance or None
        """
        return self._providers.get(platform)

    async def find_matches(
        self,
        song: Song,
        target_platforms: list[TargetPlatform] | None = None,
        limit: int = 5,
    ) -> list[Match]:
        """
        Find matches for a song on target platforms.

        Args:
            song: Song to find matches for
            target_platforms: Platforms to search (default: all enabled in user's preferred order)
            limit: Maximum matches per platform

        Returns:
            List of Match objects sorted by score
        """
        if target_platforms is None:
            # Use user's preferred platform order
            target_platforms = self._platform_order if self._platform_order else list(self._providers.keys())

        all_matches: list[Match] = []

        for platform in target_platforms:
            provider = self._providers.get(platform)
            if provider is None:
                continue

            try:
                # Search for results
                results = await provider.search(song, limit=limit * 2)

                if not results:
                    continue

                # Score and rank results using matching engine
                ordered_results = order_results(results, song)

                # Get best matches
                best_results = get_best_matches(ordered_results)[:limit]

                # Create Match objects
                for result, score in best_results:
                    match = Match(
                        source_song=song,
                        target_result=result,
                        score=score,
                        match_type="system",
                        confidence=min(score / 100, 1.0),
                    )
                    all_matches.append(match)

            except SearchError:
                continue

        # Sort all matches by score
        all_matches.sort(key=lambda m: m.score, reverse=True)

        return all_matches

    async def find_best_match(
        self,
        song: Song,
        target_platforms: list[TargetPlatform] | None = None,
    ) -> Match | None:
        """
        Find the best match for a song.

        Args:
            song: Song to match
            target_platforms: Platforms to search (default: all)

        Returns:
            Best Match or None
        """
        matches = await self.find_matches(
            song,
            target_platforms=target_platforms,
            limit=1,
        )

        return matches[0] if matches else None

    async def find_match_on_platform(
        self,
        song: Song,
        platform: TargetPlatform,
        limit: int = 5,
    ) -> list[Match]:
        """
        Find matches for a song on a specific platform.

        Args:
            song: Song to match
            platform: Target platform
            limit: Maximum number of matches

        Returns:
            List of Match objects
        """
        return await self.find_matches(
            song,
            target_platforms=[platform],
            limit=limit,
        )

    async def search_by_isrc(
        self,
        song: Song,
        platform: TargetPlatform = TargetPlatform.YOUTUBE_MUSIC,
    ) -> Match | None:
        """
        Search for a match by ISRC code.

        Args:
            song: Song with ISRC
            platform: Platform to search

        Returns:
            Match or None
        """
        if not song.isrc:
            return None

        provider = self._providers.get(platform)
        if provider is None:
            return None

        # Check if provider supports ISRC search
        if not hasattr(provider, "search_by_isrc"):
            return None

        try:
            result = await provider.search_by_isrc(song.isrc)  # type: ignore[attr-defined]
            if result is None:
                return None

            # Score the result
            ordered = order_results([result], song)
            if not ordered:
                return None

            best = get_best_matches(ordered)
            if not best:
                return None

            matched_result, score = best[0]
            return Match(
                source_song=song,
                target_result=matched_result,
                score=score,
                match_type="system",
                confidence=min(score / 100, 1.0),
            )

        except SearchError:
            return None

    async def close(self) -> None:
        """Close all target providers."""
        for provider in self._providers.values():
            await provider.close()

    @property
    def supported_platforms(self) -> list[TargetPlatform]:
        """Get list of supported target platforms."""
        return list(self._providers.keys())


# Global service instance (for default preferences)
_match_service: MatchService | None = None


def get_match_service(
    audio_preferences: list[ProviderPreference] | None = None,
) -> MatchService:
    """
    Get a match service instance.

    If audio_preferences is provided, creates a new service with those preferences.
    Otherwise returns the global service with default preferences.

    Args:
        audio_preferences: Optional user preferences for audio sources

    Returns:
        MatchService instance configured with the specified preferences
    """
    global _match_service

    # If preferences are provided, always create a new service with those preferences
    if audio_preferences is not None:
        return MatchService(audio_preferences=audio_preferences)

    # Otherwise use/create the global default service
    if _match_service is None:
        _match_service = MatchService()
    return _match_service
