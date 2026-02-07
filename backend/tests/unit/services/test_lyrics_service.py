"""Tests for LyricsService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.providers_config import ProviderPreference
from spotdl.core.services.lyrics import (
    LyricsResult,
    LyricsService,
    LyricsServiceError,
    get_lyrics_service,
)
from spotdl.db.models.lyrics import Lyrics as LyricsModel
from spotdl.providers.lyrics.azlyrics import AZLyricsProvider
from spotdl.providers.lyrics.genius import GeniusProvider, GeniusWebProvider
from spotdl.providers.lyrics.musixmatch import MusixMatchProvider
from spotdl.providers.lyrics.synced import SyncedLyricsProvider


@pytest.fixture
def song_id() -> uuid.UUID:
    """Create a test song ID."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_lyrics() -> str:
    """Create sample plain lyrics."""
    return """Verse 1
This is a test song
With some lyrics here

Chorus
La la la la la
Dancing all night long"""


@pytest.fixture
def sample_synced_lyrics() -> str:
    """Create sample synced LRC lyrics."""
    return """[00:12.00]Verse 1
[00:15.50]This is a test song
[00:18.75]With some lyrics here
[00:22.00]
[00:23.50]Chorus
[00:25.00]La la la la la
[00:28.25]Dancing all night long"""


@pytest.fixture
def lyrics_preferences() -> list[ProviderPreference]:
    """Create test lyrics preferences."""
    return [
        ProviderPreference(id="synced", name="Synced Lyrics", enabled=True),
        ProviderPreference(id="genius", name="Genius", enabled=True),
        ProviderPreference(id="musixmatch", name="MusixMatch", enabled=True),
    ]


class TestLyricsServiceInit:
    """Tests for LyricsService initialization."""

    @pytest.mark.asyncio
    async def test_init_default(self, db_session: AsyncSession) -> None:
        """Test default initialization."""
        service = LyricsService(session=db_session)
        assert service.session == db_session
        assert service.genius_token is None
        assert service.enable_cache is True
        assert service._lyrics_preferences is None
        assert service._client is None

    @pytest.mark.asyncio
    async def test_init_with_genius_token(self, db_session: AsyncSession) -> None:
        """Test initialization with Genius token."""
        service = LyricsService(
            session=db_session,
            genius_token="test_token",
        )
        assert service.genius_token == "test_token"

    @pytest.mark.asyncio
    async def test_init_cache_disabled(self, db_session: AsyncSession) -> None:
        """Test initialization with cache disabled."""
        service = LyricsService(
            session=db_session,
            enable_cache=False,
        )
        assert service.enable_cache is False

    @pytest.mark.asyncio
    async def test_init_with_preferences(
        self, db_session: AsyncSession, lyrics_preferences: list[ProviderPreference]
    ) -> None:
        """Test initialization with lyrics preferences."""
        service = LyricsService(
            session=db_session,
            lyrics_preferences=lyrics_preferences,
        )
        assert service._lyrics_preferences == lyrics_preferences

    @pytest.mark.asyncio
    async def test_context_manager(self, db_session: AsyncSession) -> None:
        """Test async context manager."""
        async with LyricsService(session=db_session) as service:
            assert service._client is not None
            assert isinstance(service._client, httpx.AsyncClient)
            client = service._client

        # Client should be closed after exit
        assert client.is_closed


class TestGetProviders:
    """Tests for provider initialization."""

    @pytest.mark.asyncio
    async def test_default_providers_no_token(self, db_session: AsyncSession) -> None:
        """Test default provider list without Genius token."""
        service = LyricsService(session=db_session)
        async with service:
            providers = service._get_providers()

            assert len(providers) == 4
            assert isinstance(providers[0], SyncedLyricsProvider)
            assert isinstance(providers[1], GeniusWebProvider)
            assert isinstance(providers[2], MusixMatchProvider)
            assert isinstance(providers[3], AZLyricsProvider)

    @pytest.mark.asyncio
    async def test_default_providers_with_token(self, db_session: AsyncSession) -> None:
        """Test default provider list with Genius token."""
        service = LyricsService(
            session=db_session,
            genius_token="test_token",
        )
        async with service:
            providers = service._get_providers()

            assert len(providers) == 4
            assert isinstance(providers[0], SyncedLyricsProvider)
            assert isinstance(providers[1], GeniusProvider)
            assert isinstance(providers[2], MusixMatchProvider)
            assert isinstance(providers[3], AZLyricsProvider)

    @pytest.mark.asyncio
    async def test_providers_with_preferences(
        self, db_session: AsyncSession, lyrics_preferences: list[ProviderPreference]
    ) -> None:
        """Test provider list respects preferences."""
        service = LyricsService(
            session=db_session,
            lyrics_preferences=lyrics_preferences,
        )
        async with service:
            providers = service._get_providers()

            # Should have 3 enabled providers
            assert len(providers) == 3
            assert isinstance(providers[0], SyncedLyricsProvider)
            assert isinstance(providers[1], GeniusWebProvider)
            assert isinstance(providers[2], MusixMatchProvider)

    @pytest.mark.asyncio
    async def test_providers_empty_preferences_fallback(
        self, db_session: AsyncSession
    ) -> None:
        """Test fallback to defaults when all providers disabled."""
        empty_prefs = [
            ProviderPreference(id="synced", name="Synced", enabled=False),
            ProviderPreference(id="genius", name="Genius", enabled=False),
        ]
        service = LyricsService(
            session=db_session,
            lyrics_preferences=empty_prefs,
        )
        async with service:
            providers = service._get_providers()
            # Should fall back to defaults
            assert len(providers) == 4

    @pytest.mark.asyncio
    async def test_create_provider_unknown(self, db_session: AsyncSession) -> None:
        """Test creating unknown provider returns None."""
        service = LyricsService(session=db_session)
        async with service:
            provider = service._create_provider("unknown_provider")
            assert provider is None


class TestFetchLyrics:
    """Tests for lyrics fetching."""

    @pytest.mark.asyncio
    async def test_fetch_lyrics_from_cache(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test fetching lyrics from cache."""
        # Add lyrics to cache
        cached_lyrics = LyricsModel(
            song_id=song_id,
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
        )
        db_session.add(cached_lyrics)
        await db_session.commit()

        service = LyricsService(session=db_session, enable_cache=True)

        result = await service.fetch_lyrics(
            song_id=song_id,
            name="Test Song",
            artists=["Test Artist"],
        )

        assert result is not None
        assert result.lyrics_text == sample_lyrics
        assert result.source == "genius"
        assert result.from_cache is True
        assert result.lyrics_synced is None

    @pytest.mark.asyncio
    async def test_fetch_synced_lyrics_from_cache(
        self,
        db_session: AsyncSession,
        song_id: uuid.UUID,
        sample_lyrics: str,
        sample_synced_lyrics: str,
    ) -> None:
        """Test fetching synced lyrics from cache is prioritized."""
        # Add plain lyrics
        plain_lyrics = LyricsModel(
            song_id=song_id,
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
        )
        db_session.add(plain_lyrics)

        # Add synced lyrics
        synced_lyrics = LyricsModel(
            song_id=song_id,
            lyrics_text=sample_lyrics,
            lyrics_synced=sample_synced_lyrics,
            source="synced",
        )
        db_session.add(synced_lyrics)
        await db_session.commit()

        service = LyricsService(session=db_session, enable_cache=True)

        result = await service.fetch_lyrics(
            song_id=song_id,
            name="Test Song",
            artists=["Test Artist"],
        )

        assert result is not None
        assert result.lyrics_synced == sample_synced_lyrics
        assert result.source == "synced"
        assert result.from_cache is True

    @pytest.mark.asyncio
    async def test_fetch_lyrics_cache_disabled(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test fetching with cache disabled ignores cached lyrics."""
        # Add lyrics to cache
        cached_lyrics = LyricsModel(
            song_id=song_id,
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
        )
        db_session.add(cached_lyrics)
        await db_session.commit()

        service = LyricsService(session=db_session, enable_cache=False)

        # Mock provider to return different lyrics
        async with service:
            with patch.object(
                service, "_fetch_from_providers", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.return_value = LyricsResult(
                    lyrics_text="New lyrics",
                    lyrics_synced=None,
                    source="musixmatch",
                    from_cache=False,
                )

                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is not None
                assert result.lyrics_text == "New lyrics"
                assert result.from_cache is False
                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_lyrics_force_refresh(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test force refresh bypasses cache."""
        # Add lyrics to cache
        cached_lyrics = LyricsModel(
            song_id=song_id,
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
        )
        db_session.add(cached_lyrics)
        await db_session.commit()

        service = LyricsService(session=db_session, enable_cache=True)

        async with service:
            with patch.object(
                service, "_fetch_from_providers", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.return_value = LyricsResult(
                    lyrics_text="Fresh lyrics",
                    lyrics_synced=None,
                    source="musixmatch",
                    from_cache=False,
                )

                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                    force_refresh=True,
                )

                assert result is not None
                assert result.lyrics_text == "Fresh lyrics"
                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_lyrics_from_provider(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test fetching lyrics from provider."""
        service = LyricsService(session=db_session, enable_cache=True)

        async with service:
            # Mock a provider
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is not None
                assert result.lyrics_text == sample_lyrics
                assert result.source == "testprovider"
                assert result.from_cache is False
                mock_provider.get_lyrics.assert_called_once_with(
                    "Test Song", ["Test Artist"]
                )

    @pytest.mark.asyncio
    async def test_fetch_lyrics_no_results(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test fetching when no lyrics found."""
        service = LyricsService(session=db_session)

        async with service:
            # Mock provider returning None
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value=None)
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_fetch_lyrics_provider_exception(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test handling provider exceptions gracefully."""
        service = LyricsService(session=db_session)

        async with service:
            # Mock provider that raises exception
            mock_provider = AsyncMock()
            mock_provider.name = "FailingProvider"
            mock_provider.get_lyrics = AsyncMock(side_effect=Exception("API Error"))
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                # Should return None instead of raising
                assert result is None

    @pytest.mark.asyncio
    async def test_fetch_lyrics_saves_to_cache(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test that fetched lyrics are saved to cache."""
        service = LyricsService(session=db_session, enable_cache=True)

        async with service:
            # Mock provider
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is not None
                await db_session.commit()

                # Verify lyrics were saved
                from sqlalchemy import select

                stmt = select(LyricsModel).where(LyricsModel.song_id == song_id)
                cached = (await db_session.execute(stmt)).scalar_one_or_none()

                assert cached is not None
                assert cached.lyrics_text == sample_lyrics
                assert cached.source == "testprovider"


class TestProviderFallback:
    """Tests for provider fallback logic."""

    @pytest.mark.asyncio
    async def test_provider_fallback_on_failure(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test fallback to next provider when first fails."""
        service = LyricsService(session=db_session)

        async with service:
            # First provider fails
            mock_provider1 = AsyncMock()
            mock_provider1.name = "FailingProvider"
            mock_provider1.get_lyrics = AsyncMock(return_value=None)
            mock_provider1.__aenter__ = AsyncMock(return_value=mock_provider1)
            mock_provider1.__aexit__ = AsyncMock()

            # Second provider succeeds
            mock_provider2 = AsyncMock()
            mock_provider2.name = "WorkingProvider"
            mock_provider2.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_provider2.__aenter__ = AsyncMock(return_value=mock_provider2)
            mock_provider2.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider1, mock_provider2]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is not None
                assert result.source == "workingprovider"
                mock_provider1.get_lyrics.assert_called_once()
                mock_provider2.get_lyrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_prioritize_synced_lyrics(
        self,
        db_session: AsyncSession,
        song_id: uuid.UUID,
        sample_lyrics: str,
        sample_synced_lyrics: str,
    ) -> None:
        """Test that synced lyrics are prioritized."""
        service = LyricsService(session=db_session)

        async with service:
            # Create mock synced provider
            mock_synced = MagicMock()
            mock_synced.name = "SyncedProvider"
            mock_synced.get_lyrics = AsyncMock(return_value=sample_synced_lyrics)
            mock_synced.__aenter__ = AsyncMock(return_value=mock_synced)
            mock_synced.__aexit__ = AsyncMock()

            # Create mock plain provider
            mock_plain = AsyncMock()
            mock_plain.name = "PlainProvider"
            mock_plain.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_plain.__aenter__ = AsyncMock(return_value=mock_plain)
            mock_plain.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_synced, mock_plain]
            ):
                # Make the service think first provider is SyncedLyricsProvider
                with patch(
                    "spotdl.core.services.lyrics.SyncedLyricsProvider",
                    return_value=mock_synced,
                ):
                    with patch.object(
                        service, "_is_lrc_format", return_value=True
                    ) as mock_is_lrc:
                        result = await service.fetch_lyrics(
                            song_id=song_id,
                            name="Test Song",
                            artists=["Test Artist"],
                        )

                        assert result is not None
                        # Should check if it's LRC format
                        assert result.lyrics_synced is not None


class TestLRCFormatHandling:
    """Tests for LRC format detection and conversion."""

    @pytest.mark.asyncio
    async def test_is_lrc_format_valid(self, db_session: AsyncSession) -> None:
        """Test LRC format detection with valid LRC."""
        service = LyricsService(session=db_session)
        lrc_text = "[00:12.00]Test line\n[00:15.50]Another line"
        assert service._is_lrc_format(lrc_text) is True

    @pytest.mark.asyncio
    async def test_is_lrc_format_invalid(self, db_session: AsyncSession) -> None:
        """Test LRC format detection with plain text."""
        service = LyricsService(session=db_session)
        plain_text = "Just plain lyrics\nNo timestamps"
        assert service._is_lrc_format(plain_text) is False

    @pytest.mark.asyncio
    async def test_lrc_to_plain(
        self, db_session: AsyncSession, sample_synced_lyrics: str
    ) -> None:
        """Test converting LRC to plain text."""
        service = LyricsService(session=db_session)
        plain = service._lrc_to_plain(sample_synced_lyrics)

        # Should not contain timestamps
        assert "[00:" not in plain
        assert "Verse 1" in plain
        assert "Chorus" in plain
        assert "La la la la la" in plain

    @pytest.mark.asyncio
    async def test_lrc_to_plain_empty_lines(self, db_session: AsyncSession) -> None:
        """Test LRC conversion removes empty lines."""
        service = LyricsService(session=db_session)
        lrc = "[00:12.00]Line 1\n[00:15.00]\n[00:18.00]Line 2"
        plain = service._lrc_to_plain(lrc)

        lines = plain.split("\n")
        assert len(lines) == 2
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"


class TestCacheOperations:
    """Tests for cache saving and retrieval."""

    @pytest.mark.asyncio
    async def test_save_to_cache_new(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test saving new lyrics to cache."""
        service = LyricsService(session=db_session, enable_cache=True)

        result = LyricsResult(
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
            from_cache=False,
        )

        await service._save_to_cache(song_id, result)
        await db_session.commit()

        # Verify saved
        from sqlalchemy import select

        stmt = select(LyricsModel).where(LyricsModel.song_id == song_id)
        cached = (await db_session.execute(stmt)).scalar_one_or_none()

        assert cached is not None
        assert cached.lyrics_text == sample_lyrics
        assert cached.source == "genius"

    @pytest.mark.asyncio
    async def test_save_to_cache_update(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test updating existing cache entry."""
        # Create existing entry
        existing = LyricsModel(
            song_id=song_id,
            lyrics_text="Old lyrics",
            lyrics_synced=None,
            source="genius",
        )
        db_session.add(existing)
        await db_session.commit()

        service = LyricsService(session=db_session, enable_cache=True)

        result = LyricsResult(
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
            from_cache=False,
        )

        await service._save_to_cache(song_id, result)
        await db_session.commit()

        # Verify updated
        from sqlalchemy import select

        stmt = select(LyricsModel).where(
            LyricsModel.song_id == song_id, LyricsModel.source == "genius"
        )
        cached = (await db_session.execute(stmt)).scalar_one_or_none()

        assert cached is not None
        assert cached.lyrics_text == sample_lyrics

    @pytest.mark.asyncio
    async def test_save_to_cache_error_handled(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test cache save errors are handled gracefully."""
        service = LyricsService(session=db_session, enable_cache=True)

        result = LyricsResult(
            lyrics_text="Test",
            lyrics_synced=None,
            source="test",
            from_cache=False,
        )

        # Mock session to raise error
        with patch.object(db_session, "execute", side_effect=Exception("DB Error")):
            # Should not raise exception
            await service._save_to_cache(song_id, result)


class TestGetLyricsForSong:
    """Tests for getting cached lyrics."""

    @pytest.mark.asyncio
    async def test_get_lyrics_for_song_found(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test getting cached lyrics."""
        # Add lyrics to cache
        cached = LyricsModel(
            song_id=song_id,
            lyrics_text=sample_lyrics,
            lyrics_synced=None,
            source="genius",
        )
        db_session.add(cached)
        await db_session.commit()

        service = LyricsService(session=db_session)
        result = await service.get_lyrics_for_song(song_id)

        assert result is not None
        assert result.lyrics_text == sample_lyrics
        assert result.source == "genius"
        assert result.from_cache is True

    @pytest.mark.asyncio
    async def test_get_lyrics_for_song_not_found(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test getting lyrics when not cached."""
        service = LyricsService(session=db_session)
        result = await service.get_lyrics_for_song(song_id)

        assert result is None


class TestFetchAllLyrics:
    """Tests for fetching from all providers."""

    @pytest.mark.asyncio
    async def test_fetch_all_lyrics(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test fetching lyrics from all providers."""
        service = LyricsService(session=db_session)

        async with service:
            # Mock multiple providers
            mock_provider1 = AsyncMock()
            mock_provider1.name = "Provider1"
            mock_provider1.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_provider1.__aenter__ = AsyncMock(return_value=mock_provider1)
            mock_provider1.__aexit__ = AsyncMock()

            mock_provider2 = AsyncMock()
            mock_provider2.name = "Provider2"
            mock_provider2.get_lyrics = AsyncMock(return_value="Different lyrics")
            mock_provider2.__aenter__ = AsyncMock(return_value=mock_provider2)
            mock_provider2.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider1, mock_provider2]
            ):
                results = await service.fetch_all_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert len(results) == 2
                assert results[0].lyrics_text == sample_lyrics
                assert results[0].source == "provider1"
                assert results[1].lyrics_text == "Different lyrics"
                assert results[1].source == "provider2"

    @pytest.mark.asyncio
    async def test_fetch_all_lyrics_saves_to_db(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test that fetch_all_lyrics saves results to database."""
        service = LyricsService(session=db_session)

        async with service:
            # Mock provider
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                results = await service.fetch_all_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert len(results) == 1
                await db_session.commit()

                # Verify saved to DB
                from sqlalchemy import select

                stmt = select(LyricsModel).where(LyricsModel.song_id == song_id)
                cached = (await db_session.execute(stmt)).scalar_one_or_none()

                assert cached is not None
                assert cached.quality_score is not None
                assert cached.line_count is not None
                assert cached.content_hash is not None

    @pytest.mark.asyncio
    async def test_fetch_all_lyrics_handles_failures(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test fetch_all_lyrics handles provider failures."""
        service = LyricsService(session=db_session)

        async with service:
            # One failing, one succeeding provider
            mock_fail = AsyncMock()
            mock_fail.name = "FailProvider"
            mock_fail.get_lyrics = AsyncMock(side_effect=Exception("Error"))
            mock_fail.__aenter__ = AsyncMock(return_value=mock_fail)
            mock_fail.__aexit__ = AsyncMock()

            mock_success = AsyncMock()
            mock_success.name = "SuccessProvider"
            mock_success.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_success.__aenter__ = AsyncMock(return_value=mock_success)
            mock_success.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_fail, mock_success]
            ):
                results = await service.fetch_all_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                # Should only have one result from successful provider
                assert len(results) == 1
                assert results[0].source == "successprovider"


class TestGetAllLyricsForSong:
    """Tests for getting all cached lyrics for a song."""

    @pytest.mark.asyncio
    async def test_get_all_lyrics_for_song(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test getting all cached lyrics from multiple sources."""
        # Add multiple lyrics entries
        lyrics1 = LyricsModel(
            song_id=song_id,
            lyrics_text="Lyrics from source 1",
            lyrics_synced=None,
            source="genius",
        )
        lyrics2 = LyricsModel(
            song_id=song_id,
            lyrics_text="Lyrics from source 2",
            lyrics_synced=None,
            source="musixmatch",
        )
        db_session.add(lyrics1)
        db_session.add(lyrics2)
        await db_session.commit()

        service = LyricsService(session=db_session)
        results = await service.get_all_lyrics_for_song(song_id)

        assert len(results) == 2
        sources = [r.source for r in results]
        assert "genius" in sources
        assert "musixmatch" in sources
        assert all(r.from_cache for r in results)

    @pytest.mark.asyncio
    async def test_get_all_lyrics_for_song_empty(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test getting lyrics when none cached."""
        service = LyricsService(session=db_session)
        results = await service.get_all_lyrics_for_song(song_id)

        assert len(results) == 0


class TestQualityScore:
    """Tests for quality score calculation."""

    @pytest.mark.asyncio
    async def test_quality_score_base(self, db_session: AsyncSession) -> None:
        """Test base quality score."""
        service = LyricsService(session=db_session)
        score = service._calculate_quality_score(
            lyrics_text="Short",
            lyrics_synced=None,
            source="unknown",
        )
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_quality_score_synced_bonus(self, db_session: AsyncSession) -> None:
        """Test synced lyrics bonus."""
        service = LyricsService(session=db_session)
        score = service._calculate_quality_score(
            lyrics_text="Short",
            lyrics_synced="[00:00.00]Short",
            source="unknown",
        )
        assert score == 0.8  # 0.5 base + 0.3 synced

    @pytest.mark.asyncio
    async def test_quality_score_length_bonus(self, db_session: AsyncSession) -> None:
        """Test length bonus."""
        service = LyricsService(session=db_session)
        long_lyrics = "A" * 150  # More than 100 chars
        score = service._calculate_quality_score(
            lyrics_text=long_lyrics,
            lyrics_synced=None,
            source="unknown",
        )
        assert score == 0.6  # 0.5 base + 0.1 length

    @pytest.mark.asyncio
    async def test_quality_score_reliable_source_bonus(
        self, db_session: AsyncSession
    ) -> None:
        """Test reliable source bonus."""
        service = LyricsService(session=db_session)
        score = service._calculate_quality_score(
            lyrics_text="Short",
            lyrics_synced=None,
            source="genius",
        )
        assert score == 0.6  # 0.5 base + 0.1 source

    @pytest.mark.asyncio
    async def test_quality_score_max(self, db_session: AsyncSession) -> None:
        """Test quality score is capped at 1.0."""
        service = LyricsService(session=db_session)
        long_lyrics = "A" * 150
        score = service._calculate_quality_score(
            lyrics_text=long_lyrics,
            lyrics_synced="[00:00.00]" + long_lyrics,
            source="genius",
        )
        assert score == 1.0  # Capped at 1.0


class TestFactoryFunction:
    """Tests for get_lyrics_service factory function."""

    @pytest.mark.asyncio
    async def test_factory_default(self, db_session: AsyncSession) -> None:
        """Test factory with default parameters."""
        service = get_lyrics_service(db_session)
        assert isinstance(service, LyricsService)
        assert service.session == db_session
        assert service.genius_token is None
        assert service.enable_cache is True

    @pytest.mark.asyncio
    async def test_factory_with_params(
        self, db_session: AsyncSession, lyrics_preferences: list[ProviderPreference]
    ) -> None:
        """Test factory with all parameters."""
        service = get_lyrics_service(
            session=db_session,
            genius_token="test_token",
            enable_cache=False,
            lyrics_preferences=lyrics_preferences,
        )
        assert service.genius_token == "test_token"
        assert service.enable_cache is False
        assert service._lyrics_preferences == lyrics_preferences


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_lyrics_text(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test handling empty lyrics text."""
        service = LyricsService(session=db_session)

        async with service:
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value="")
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                # Empty string should be treated as no result
                assert result is None

    @pytest.mark.asyncio
    async def test_no_providers_configured(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test handling when no providers are configured."""
        service = LyricsService(session=db_session)

        async with service:
            with patch.object(service, "_get_providers", return_value=[]):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_empty_artists_list(
        self, db_session: AsyncSession, song_id: uuid.UUID, sample_lyrics: str
    ) -> None:
        """Test handling empty artists list."""
        service = LyricsService(session=db_session)

        async with service:
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value=sample_lyrics)
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=[],
                )

                assert result is not None
                mock_provider.get_lyrics.assert_called_once_with("Test Song", [])

    @pytest.mark.asyncio
    async def test_unicode_lyrics(
        self, db_session: AsyncSession, song_id: uuid.UUID
    ) -> None:
        """Test handling lyrics with unicode characters."""
        unicode_lyrics = "Test lyrics with émojis 🎵 and spëcial çhars"
        service = LyricsService(session=db_session)

        async with service:
            mock_provider = AsyncMock()
            mock_provider.name = "TestProvider"
            mock_provider.get_lyrics = AsyncMock(return_value=unicode_lyrics)
            mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
            mock_provider.__aexit__ = AsyncMock()

            with patch.object(
                service, "_get_providers", return_value=[mock_provider]
            ):
                result = await service.fetch_lyrics(
                    song_id=song_id,
                    name="Test Song",
                    artists=["Test Artist"],
                )

                assert result is not None
                assert result.lyrics_text == unicode_lyrics
