"""Unit tests for spotdl_core.download.downloader module."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

from spotdl_core.download.downloader import (
    DownloadError,
    DownloadMeta,
    DownloadProgress,
    Downloader,
    DownloadSettings,
    _format_eta,
    _format_speed,
)


# ── Test Data ───────────────────────────────────────────────────────


@pytest.fixture
def sample_meta() -> DownloadMeta:
    """Sample metadata for testing."""
    return DownloadMeta(
        title="Test Song",
        artist="Test Artist",
        artists=["Test Artist", "Featured Artist"],
        album="Test Album",
        album_artist="Test Artist",
        cover_url="https://example.com/cover.jpg",
        duration=180,
        genres=["Pop", "Rock"],
        year=2024,
        date="2024-01-15",
        track_number=5,
        disc_number=1,
        disc_count=2,
        tracks_count=10,
        isrc="USRC12345678",
        publisher="Test Publisher",
        song_id="spotify:track:123",
        song_url="https://open.spotify.com/track/123",
        lyrics="Test lyrics\nLine 2",
        explicit=False,
        list_name="Test Playlist",
        list_position=3,
        list_length=20,
    )


@pytest.fixture
def basic_settings() -> DownloadSettings:
    """Basic download settings."""
    return DownloadSettings(
        audio_format="mp3",
        audio_quality="320k",
        output_template="{artist} - {title}",
        embed_metadata=True,
        embed_lyrics=True,
        embed_cover=True,
    )


@pytest.fixture
def downloader(basic_settings: DownloadSettings) -> Downloader:
    """Create a downloader instance."""
    return Downloader(basic_settings)


# ── 1. Downloader Initialization and Configuration ─────────────────


class TestDownloaderInitialization:
    """Test downloader initialization and configuration."""

    def test_init_with_settings(self, basic_settings: DownloadSettings) -> None:
        """Test initialization with custom settings."""
        downloader = Downloader(basic_settings)
        assert downloader._settings == basic_settings
        assert downloader._http_client is None

    def test_init_with_default_settings(self) -> None:
        """Test initialization with default settings."""
        downloader = Downloader()
        assert downloader._settings is not None
        assert downloader._settings.audio_format == "mp3"
        assert downloader._settings.audio_quality == "best"
        assert downloader._http_client is None

    def test_settings_validation(self) -> None:
        """Test various settings configurations."""
        settings = DownloadSettings(
            audio_format="flac",
            audio_quality="best",
            bitrate="320",
            output_template="{artist}/{album}/{track-number}. {title}",
            max_filename_length=200,
            restrict="strict",
            overwrite="force",
            embed_metadata=False,
            embed_lyrics=False,
            embed_cover=False,
            id3_separator="; ",
            sponsor_block=True,
            sponsor_block_categories=["sponsor", "intro"],
            generate_lrc=True,
            playlist_numbering=True,
            skip_explicit=True,
            ffmpeg_args="-ac 2",
            yt_dlp_args="--no-playlist",
            proxy="http://proxy.example.com:8080",
        )
        downloader = Downloader(settings)
        assert downloader._settings.audio_format == "flac"
        assert downloader._settings.sponsor_block is True
        assert downloader._settings.playlist_numbering is True

    @pytest.mark.asyncio
    async def test_get_http_client_creates_client(self, downloader: Downloader) -> None:
        """Test HTTP client creation."""
        client = await downloader._get_http_client()
        assert client is not None
        assert downloader._http_client is client

    @pytest.mark.asyncio
    async def test_get_http_client_reuses_existing(self, downloader: Downloader) -> None:
        """Test HTTP client reuse."""
        client1 = await downloader._get_http_client()
        client2 = await downloader._get_http_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_http_client_with_proxy(self) -> None:
        """Test HTTP client with proxy configuration."""
        settings = DownloadSettings(proxy="http://proxy.example.com:8080")
        downloader = Downloader(settings)
        with patch("httpx.AsyncClient") as mock_client:
            await downloader._get_http_client()
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args[1]
            assert call_kwargs["proxy"] == "http://proxy.example.com:8080"

    @pytest.mark.asyncio
    async def test_close_closes_client(self, downloader: Downloader) -> None:
        """Test closing HTTP client."""
        client = await downloader._get_http_client()
        await downloader.close()
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_close_with_no_client(self, downloader: Downloader) -> None:
        """Test closing when no client exists."""
        await downloader.close()
        assert downloader._http_client is None


# ── 2. Filename Templating ─────────────────────────────────────────


class TestFilenameTemplating:
    """Test filename generation and sanitization."""

    def test_get_output_template_basic(
        self, downloader: Downloader, sample_meta: DownloadMeta
    ) -> None:
        """Test basic template rendering."""
        result = downloader.get_output_template(sample_meta)
        assert result == "Test Artist - Test Song"

    def test_get_output_template_with_album(self, sample_meta: DownloadMeta) -> None:
        """Test template with album information."""
        settings = DownloadSettings(output_template="{artist}/{album}/{title}")
        downloader = Downloader(settings)
        result = downloader.get_output_template(sample_meta)
        assert result == "Test Artist/Test Album/Test Song"

    def test_get_output_template_with_track_number(self, sample_meta: DownloadMeta) -> None:
        """Test template with track numbering."""
        settings = DownloadSettings(output_template="{track-number}. {title}")
        downloader = Downloader(settings)
        result = downloader.get_output_template(sample_meta)
        assert result == "05. Test Song"

    def test_get_output_template_playlist_numbering(self, sample_meta: DownloadMeta) -> None:
        """Test playlist numbering prefix."""
        settings = DownloadSettings(
            output_template="{artist} - {title}",
            playlist_numbering=True,
        )
        downloader = Downloader(settings)
        result = downloader.get_output_template(sample_meta)
        assert result == "03. Test Artist - Test Song"

    def test_get_output_template_multiple_artists(self, sample_meta: DownloadMeta) -> None:
        """Test template with multiple artists."""
        settings = DownloadSettings(output_template="{artists} - {title}")
        downloader = Downloader(settings)
        result = downloader.get_output_template(sample_meta)
        assert result == "Test Artist, Featured Artist - Test Song"

    def test_get_output_template_all_placeholders(self, sample_meta: DownloadMeta) -> None:
        """Test template with all available placeholders."""
        settings = DownloadSettings(
            output_template=(
                "{artist}/{album}/{track-number}. {title} "
                "[{year}] [{genre}] [{isrc}] [{publisher}]"
            )
        )
        downloader = Downloader(settings)
        result = downloader.get_output_template(sample_meta)
        assert "Test Artist" in result
        assert "Test Album" in result
        assert "05. Test Song" in result
        assert "[2024]" in result
        assert "[Pop]" in result
        assert "[USRC12345678]" in result
        assert "[Test Publisher]" in result

    def test_get_output_template_missing_metadata(self) -> None:
        """Test template with missing metadata."""
        settings = DownloadSettings(
            output_template="{artist}/{album}/{year}/{title}"
        )
        downloader = Downloader(settings)
        meta = DownloadMeta(title="Song", artist="Artist")
        result = downloader.get_output_template(meta)
        assert result == "Artist/Unknown/Unknown/Song"

    def test_sanitize_filename_basic(self, downloader: Downloader) -> None:
        """Test basic filename sanitization."""
        result = downloader.sanitize_filename("Test Song.mp3")
        assert result == "Test Song.mp3"

    def test_sanitize_filename_invalid_chars(self, downloader: Downloader) -> None:
        """Test sanitization of invalid characters."""
        result = downloader.sanitize_filename('Test<>:"/\\|?*Song')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "/" not in result
        assert "\\" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_sanitize_filename_strict_mode(self) -> None:
        """Test strict sanitization mode."""
        settings = DownloadSettings(restrict="strict")
        downloader = Downloader(settings)
        with patch("yt_dlp.utils.sanitize_filename") as mock_sanitize:
            mock_sanitize.return_value = "clean_name"
            result = downloader.sanitize_filename("Test Song!")
            mock_sanitize.assert_called_once_with("Test Song!", restricted=True)
            assert result == "clean_name"

    def test_sanitize_filename_loose_mode(self) -> None:
        """Test loose sanitization mode (ASCII only)."""
        settings = DownloadSettings(restrict="loose")
        downloader = Downloader(settings)
        result = downloader.sanitize_filename("Tëst Sõng")
        assert result.isascii()

    def test_sanitize_filename_empty(self, downloader: Downloader) -> None:
        """Test sanitization of empty string."""
        result = downloader.sanitize_filename("")
        assert result == "Unknown"

    def test_sanitize_filename_long(self, downloader: Downloader) -> None:
        """Test sanitization of very long filename."""
        long_name = "a" * 300
        result = downloader.sanitize_filename(long_name)
        assert len(result) == 200

    def test_limit_filename_length_no_truncation(
        self, downloader: Downloader, sample_meta: DownloadMeta
    ) -> None:
        """Test filename length limiting without truncation needed."""
        result = downloader._limit_filename_length("Short Name", sample_meta)
        assert result == "Short Name"

    def test_limit_filename_length_with_truncation(self, sample_meta: DownloadMeta) -> None:
        """Test filename length limiting with truncation."""
        settings = DownloadSettings(max_filename_length=30)
        downloader = Downloader(settings)
        long_name = "a" * 100
        result = downloader._limit_filename_length(long_name, sample_meta)
        assert len(result) <= 30 - 4  # Account for extension


# ── 3. yt-dlp Options ───────────────────────────────────────────────


class TestYtDlpOptions:
    """Test yt-dlp options generation."""

    def test_get_yt_dlp_options_basic(self, downloader: Downloader, tmp_path: Path) -> None:
        """Test basic yt-dlp options generation."""
        output_path = tmp_path / "output"
        options = downloader.get_yt_dlp_options(output_path)

        assert options["format"] == "bestaudio/best"
        assert options["outtmpl"] == str(output_path)
        assert options["quiet"] is True
        assert options["no_warnings"] is True
        assert "postprocessors" in options

    def test_get_yt_dlp_options_format_conversion(self, tmp_path: Path) -> None:
        """Test format conversion options."""
        settings = DownloadSettings(audio_format="flac", audio_quality="best")
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        postprocessors = options["postprocessors"]
        assert any(p["key"] == "FFmpegExtractAudio" for p in postprocessors)
        extract_audio = next(p for p in postprocessors if p["key"] == "FFmpegExtractAudio")
        assert extract_audio["preferredcodec"] == "flac"

    def test_get_yt_dlp_options_bitrate_settings(self, tmp_path: Path) -> None:
        """Test bitrate configuration."""
        settings = DownloadSettings(audio_format="mp3", bitrate="192")
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        extract_audio = next(
            p for p in options["postprocessors"] if p["key"] == "FFmpegExtractAudio"
        )
        assert extract_audio["preferredquality"] == "192"

    def test_get_yt_dlp_options_disable_bitrate(self, tmp_path: Path) -> None:
        """Test disabled bitrate conversion."""
        settings = DownloadSettings(bitrate="disable")
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        # Should not have FFmpegExtractAudio postprocessor
        extract_audio = [
            p for p in options["postprocessors"] if p["key"] == "FFmpegExtractAudio"
        ]
        assert len(extract_audio) == 0

    def test_get_yt_dlp_options_sponsor_block(self, tmp_path: Path) -> None:
        """Test SponsorBlock integration."""
        settings = DownloadSettings(
            sponsor_block=True,
            sponsor_block_categories=["sponsor", "intro"],
        )
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        postprocessors = options["postprocessors"]
        assert any(p["key"] == "SponsorBlock" for p in postprocessors)
        assert any(p["key"] == "ModifyChapters" for p in postprocessors)

    def test_get_yt_dlp_options_cookies(self, tmp_path: Path) -> None:
        """Test cookies file configuration."""
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text("# Netscape HTTP Cookie File")

        settings = DownloadSettings(cookies_path=cookies_file)
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        assert options["cookiefile"] == str(cookies_file)

    def test_get_yt_dlp_options_proxy(self, tmp_path: Path) -> None:
        """Test proxy configuration."""
        settings = DownloadSettings(proxy="http://proxy.example.com:8080")
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        assert options["proxy"] == "http://proxy.example.com:8080"

    def test_get_yt_dlp_options_ffmpeg_args(self, tmp_path: Path) -> None:
        """Test FFmpeg arguments."""
        settings = DownloadSettings(ffmpeg_args="-ac 2 -ar 44100")
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        assert "postprocessor_args" in options
        assert options["postprocessor_args"]["ffmpeg"] == ["-ac", "2", "-ar", "44100"]

    def test_get_yt_dlp_options_custom_args(self, tmp_path: Path) -> None:
        """Test custom yt-dlp arguments."""
        settings = DownloadSettings(yt_dlp_args="--no-playlist --age-limit 18")
        downloader = Downloader(settings)
        options = downloader.get_yt_dlp_options(tmp_path / "output")

        assert options["no_playlist"] is True
        assert options["age_limit"] == "18"

    def test_get_yt_dlp_options_progress_callback(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test progress callback hook."""
        progress_data = []

        def callback(progress: DownloadProgress) -> None:
            progress_data.append(progress)

        options = downloader.get_yt_dlp_options(tmp_path / "output", callback)
        assert "progress_hooks" in options

        # Simulate progress hook call
        hook = options["progress_hooks"][0]
        hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})

        assert len(progress_data) == 1
        assert progress_data[0].status == "downloading"
        assert progress_data[0].progress == 50.0


# ── 4. Download Operations ──────────────────────────────────────────


class TestDownloadOperations:
    """Test download operations."""

    @pytest.mark.asyncio
    async def test_download_success(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test successful download."""
        output_file = tmp_path / "Test Artist - Test Song.mp3"

        def create_file(*args: Any, **kwargs: Any) -> None:
            output_file.touch()

        with patch.object(Downloader, "_run_yt_dlp", side_effect=create_file) as mock_yt_dlp:
            result = await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                tmp_path,
            )

            assert result == output_file
            mock_yt_dlp.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_skip_existing(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test skipping existing file."""
        output_file = tmp_path / "Test Artist - Test Song.mp3"
        output_file.touch()

        with patch.object(Downloader, "_run_yt_dlp") as mock_yt_dlp:
            result = await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                tmp_path,
            )

            assert result == output_file
            mock_yt_dlp.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_force_overwrite(
        self, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test force overwriting existing file."""
        settings = DownloadSettings(overwrite="force")
        downloader = Downloader(settings)
        output_file = tmp_path / "Test Artist - Test Song.mp3"
        output_file.write_text("old content")

        def create_file(*args: Any, **kwargs: Any) -> None:
            output_file.touch()

        with patch.object(Downloader, "_run_yt_dlp", side_effect=create_file) as mock_yt_dlp:
            result = await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                tmp_path,
            )

            assert result == output_file
            mock_yt_dlp.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_metadata_only(
        self, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test metadata-only update mode."""
        settings = DownloadSettings(overwrite="metadata")
        downloader = Downloader(settings)
        output_file = tmp_path / "Test Artist - Test Song.mp3"
        output_file.touch()

        with patch.object(Downloader, "_run_yt_dlp") as mock_yt_dlp:
            result = await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                tmp_path,
            )

            assert result == output_file
            mock_yt_dlp.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_creates_output_directory(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test output directory creation."""
        nested_dir = tmp_path / "music" / "albums" / "2024"
        output_file = nested_dir / "Test Artist - Test Song.mp3"

        def create_file(*args: Any, **kwargs: Any) -> None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.touch()

        with patch.object(Downloader, "_run_yt_dlp", side_effect=create_file):
            await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                nested_dir,
            )

            assert nested_dir.exists()

    @pytest.mark.asyncio
    async def test_download_with_progress_callback(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test download with progress callback."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        output_file = tmp_path / "Test Artist - Test Song.mp3"

        with patch.object(Downloader, "_run_yt_dlp"):
            output_file.touch()

            await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                tmp_path,
                callback,
            )

    @pytest.mark.asyncio
    async def test_download_file_not_found(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test error when output file not found."""
        with patch.object(Downloader, "_run_yt_dlp"):
            with pytest.raises(DownloadError, match="Output file not found"):
                await downloader.download(
                    "https://www.youtube.com/watch?v=test",
                    sample_meta,
                    tmp_path,
                )

    @pytest.mark.asyncio
    async def test_download_yt_dlp_error(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test error handling for yt-dlp failures."""
        with patch.object(Downloader, "_run_yt_dlp", side_effect=Exception("Network error")):
            with pytest.raises(DownloadError, match="Download failed"):
                await downloader.download(
                    "https://www.youtube.com/watch?v=test",
                    sample_meta,
                    tmp_path,
                )

    def test_find_output_file_exact_match(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test finding output file with exact extension match."""
        expected = tmp_path / "test.mp3"
        expected.touch()

        result = downloader._find_output_file(tmp_path / "test")
        assert result == expected

    def test_find_output_file_alternative_format(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test finding output file with alternative format."""
        expected = tmp_path / "test.m4a"
        expected.touch()

        result = downloader._find_output_file(tmp_path / "test")
        assert result == expected

    def test_find_output_file_not_found(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test file not found."""
        result = downloader._find_output_file(tmp_path / "nonexistent")
        assert result is None

    def test_run_yt_dlp(self) -> None:
        """Test yt-dlp execution."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl

            Downloader._run_yt_dlp("https://www.youtube.com/watch?v=test", {})

            mock_ydl.download.assert_called_once_with(["https://www.youtube.com/watch?v=test"])


# ── 5. Metadata Embedding ───────────────────────────────────────────


class TestMetadataEmbedding:
    """Test metadata embedding for various formats."""

    @pytest.mark.asyncio
    async def test_embed_metadata_disabled(
        self, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test metadata embedding when disabled."""
        settings = DownloadSettings(embed_metadata=False)
        downloader = Downloader(settings)
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        await downloader.embed_metadata(file_path, sample_meta)
        # Should do nothing without errors

    @pytest.mark.asyncio
    async def test_embed_mp3_metadata(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test MP3 metadata embedding."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        with patch("mutagen.easyid3.EasyID3") as mock_id3:
            mock_audio = MagicMock()
            mock_id3.return_value = mock_audio

            await downloader.embed_metadata(file_path, sample_meta)

            mock_audio.__setitem__.assert_any_call("title", sample_meta.title)
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_mp3_metadata_no_header(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test MP3 metadata embedding with missing ID3 header."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        from mutagen.id3 import ID3NoHeaderError

        with patch("mutagen.easyid3.EasyID3") as mock_id3:
            # First call raises error, second succeeds
            mock_id3.side_effect = [
                ID3NoHeaderError(),
                MagicMock(),
                MagicMock(),
            ]

            await downloader.embed_metadata(file_path, sample_meta)

    @pytest.mark.asyncio
    async def test_embed_mp3_cover(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test MP3 cover art embedding."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        with patch("mutagen.id3.ID3") as mock_id3, \
             patch.object(downloader, "_download_cover", return_value=b"fake_image"):

            mock_audio = MagicMock()
            mock_id3.return_value = mock_audio

            await downloader._embed_mp3_cover(file_path, "https://example.com/cover.jpg")

            mock_audio.delall.assert_called_with("APIC")
            mock_audio.add.assert_called()
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_m4a_metadata(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test M4A metadata embedding."""
        file_path = tmp_path / "test.m4a"
        file_path.touch()

        with patch("mutagen.mp4.MP4") as mock_mp4:
            mock_audio = MagicMock()
            mock_mp4.return_value = mock_audio

            await downloader.embed_metadata(file_path, sample_meta)

            mock_audio.__setitem__.assert_any_call("\xa9nam", [sample_meta.title])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_m4a_cover(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test M4A cover art embedding."""
        file_path = tmp_path / "test.m4a"
        file_path.touch()

        with patch("mutagen.mp4.MP4") as mock_mp4, \
             patch("mutagen.mp4.MP4Cover") as mock_cover, \
             patch.object(downloader, "_download_cover", return_value=b"fake_image"):

            mock_audio = MagicMock()
            mock_mp4.return_value = mock_audio
            mock_cover.return_value = "cover_object"

            await downloader._embed_m4a_cover(file_path, "https://example.com/cover.jpg")

            mock_audio.__setitem__.assert_called_with("covr", ["cover_object"])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_flac_metadata(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test FLAC metadata embedding."""
        file_path = tmp_path / "test.flac"
        file_path.touch()

        with patch("mutagen.flac.FLAC") as mock_flac:
            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio

            await downloader.embed_metadata(file_path, sample_meta)

            mock_audio.__setitem__.assert_any_call("title", [sample_meta.title])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_flac_cover(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test FLAC cover art embedding."""
        file_path = tmp_path / "test.flac"
        file_path.touch()

        with patch("mutagen.flac.FLAC") as mock_flac, \
             patch("mutagen.flac.Picture") as mock_picture, \
             patch.object(downloader, "_download_cover", return_value=b"fake_image"):

            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio
            mock_pic = MagicMock()
            mock_picture.return_value = mock_pic

            await downloader._embed_flac_cover(file_path, "https://example.com/cover.jpg")

            mock_audio.clear_pictures.assert_called()
            mock_audio.add_picture.assert_called_with(mock_pic)
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_opus_metadata(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test Opus metadata embedding."""
        file_path = tmp_path / "test.opus"
        file_path.touch()

        with patch("mutagen.oggopus.OggOpus") as mock_opus:
            mock_audio = MagicMock()
            mock_opus.return_value = mock_audio

            await downloader.embed_metadata(file_path, sample_meta)

            mock_audio.__setitem__.assert_any_call("title", [sample_meta.title])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_ogg_metadata(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test OGG Vorbis metadata embedding."""
        file_path = tmp_path / "test.ogg"
        file_path.touch()

        with patch("mutagen.oggvorbis.OggVorbis") as mock_ogg:
            mock_audio = MagicMock()
            mock_ogg.return_value = mock_audio

            await downloader.embed_metadata(file_path, sample_meta)

            mock_audio.__setitem__.assert_any_call("title", [sample_meta.title])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_ogg_cover(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test OGG cover art embedding."""
        file_path = tmp_path / "test.ogg"
        file_path.touch()

        with patch("mutagen.oggvorbis.OggVorbis") as mock_ogg, \
             patch("mutagen.flac.Picture") as mock_picture, \
             patch.object(downloader, "_download_cover", return_value=b"fake_image"):

            mock_audio = MagicMock()
            mock_ogg.return_value = mock_audio
            mock_pic = MagicMock()
            mock_pic.write.return_value = b"encoded"
            mock_picture.return_value = mock_pic

            await downloader._embed_ogg_cover(file_path, "https://example.com/cover.jpg")

            mock_audio.__setitem__.assert_called()
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_unsupported_format(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test metadata embedding for unsupported format."""
        file_path = tmp_path / "test.wav"
        file_path.touch()

        # Should log warning but not raise
        await downloader.embed_metadata(file_path, sample_meta)

    @pytest.mark.asyncio
    async def test_embed_metadata_error_handling(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test error handling in metadata embedding."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        with patch("mutagen.easyid3.EasyID3", side_effect=Exception("Mutagen error")):
            # Should log error but not raise
            await downloader.embed_metadata(file_path, sample_meta)


# ── 6. Lyrics Embedding ─────────────────────────────────────────────


class TestLyricsEmbedding:
    """Test lyrics embedding."""

    @pytest.mark.asyncio
    async def test_embed_lyrics_disabled(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test lyrics embedding when disabled."""
        settings = DownloadSettings(embed_lyrics=False)
        downloader = Downloader(settings)
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        await downloader.embed_lyrics(file_path, "Test lyrics")
        # Should do nothing

    @pytest.mark.asyncio
    async def test_embed_lyrics_empty(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test lyrics embedding with empty lyrics."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        await downloader.embed_lyrics(file_path, "")
        # Should do nothing

    @pytest.mark.asyncio
    async def test_embed_mp3_lyrics(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test MP3 lyrics embedding."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()
        lyrics = "Line 1\nLine 2\nLine 3"

        with patch("mutagen.id3.ID3") as mock_id3:
            mock_audio = MagicMock()
            mock_id3.return_value = mock_audio

            await downloader.embed_lyrics(file_path, lyrics)

            mock_audio.delall.assert_called_with("USLT")
            mock_audio.add.assert_called()
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_m4a_lyrics(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test M4A lyrics embedding."""
        file_path = tmp_path / "test.m4a"
        file_path.touch()
        lyrics = "Test lyrics"

        with patch("mutagen.mp4.MP4") as mock_mp4:
            mock_audio = MagicMock()
            mock_mp4.return_value = mock_audio

            await downloader.embed_lyrics(file_path, lyrics)

            mock_audio.__setitem__.assert_called_with("\xa9lyr", [lyrics])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_flac_lyrics(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test FLAC lyrics embedding."""
        file_path = tmp_path / "test.flac"
        file_path.touch()
        lyrics = "Test lyrics"

        with patch("mutagen.flac.FLAC") as mock_flac:
            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio

            await downloader.embed_lyrics(file_path, lyrics)

            mock_audio.__setitem__.assert_called_with("lyrics", [lyrics])
            mock_audio.save.assert_called()

    @pytest.mark.asyncio
    async def test_embed_lyrics_unsupported_format(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test lyrics embedding for unsupported format."""
        file_path = tmp_path / "test.opus"
        file_path.touch()

        # Should do nothing without error
        await downloader.embed_lyrics(file_path, "Test lyrics")


# ── 7. Cover Download ───────────────────────────────────────────────


class TestCoverDownload:
    """Test cover art download."""

    @pytest.mark.asyncio
    async def test_download_cover_success(self, downloader: Downloader) -> None:
        """Test successful cover download."""
        mock_response = MagicMock()
        mock_response.content = b"fake_image_data"

        with patch.object(downloader, "_get_http_client") as mock_client:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_response
            mock_client.return_value = mock_http

            result = await downloader._download_cover("https://example.com/cover.jpg")

            assert result == b"fake_image_data"
            mock_http.get.assert_called_once_with("https://example.com/cover.jpg")

    @pytest.mark.asyncio
    async def test_download_cover_http_error(self, downloader: Downloader) -> None:
        """Test cover download with HTTP error."""
        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=Mock()
        )

        with patch.object(downloader, "_get_http_client") as mock_client:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_response
            mock_client.return_value = mock_http

            result = await downloader._download_cover("https://example.com/cover.jpg")

            assert result is None

    @pytest.mark.asyncio
    async def test_download_cover_network_error(self, downloader: Downloader) -> None:
        """Test cover download with network error."""
        with patch.object(downloader, "_get_http_client") as mock_client:
            mock_http = AsyncMock()
            mock_http.get.side_effect = Exception("Network error")
            mock_client.return_value = mock_http

            result = await downloader._download_cover("https://example.com/cover.jpg")

            assert result is None


# ── 8. Helper Functions ─────────────────────────────────────────────


class TestHelperFunctions:
    """Test utility helper functions."""

    def test_format_speed_bytes(self) -> None:
        """Test speed formatting in bytes per second."""
        assert _format_speed(500) == "500 B/s"

    def test_format_speed_kilobytes(self) -> None:
        """Test speed formatting in kilobytes per second."""
        assert _format_speed(1024 * 50) == "50.0 KB/s"

    def test_format_speed_megabytes(self) -> None:
        """Test speed formatting in megabytes per second."""
        assert _format_speed(1024 * 1024 * 5) == "5.0 MB/s"

    def test_format_eta_seconds(self) -> None:
        """Test ETA formatting in seconds."""
        assert _format_eta(45) == "45s"

    def test_format_eta_minutes(self) -> None:
        """Test ETA formatting in minutes."""
        assert _format_eta(125) == "2m 5s"

    def test_format_eta_hours(self) -> None:
        """Test ETA formatting in hours."""
        assert _format_eta(7325) == "2h 2m"


# ── 9. Progress Callbacks ───────────────────────────────────────────


class TestProgressCallbacks:
    """Test progress callback functionality."""

    @pytest.mark.asyncio
    async def test_progress_callback_downloading(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test progress callback during download."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        options = downloader.get_yt_dlp_options(tmp_path / "output", callback)
        hook = options["progress_hooks"][0]

        # Simulate download progress
        hook({
            "status": "downloading",
            "downloaded_bytes": 50_000_000,
            "total_bytes": 100_000_000,
            "_speed_str": "1.5 MB/s",
            "_eta_str": "30s",
            "filename": "test.mp3",
        })

        assert len(progress_updates) == 1
        assert progress_updates[0].status == "downloading"
        assert progress_updates[0].progress == 50.0
        assert progress_updates[0].speed == "1.5 MB/s"
        assert progress_updates[0].eta == "30s"
        assert progress_updates[0].filename == "test.mp3"

    @pytest.mark.asyncio
    async def test_progress_callback_finished(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test progress callback when finished."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        options = downloader.get_yt_dlp_options(tmp_path / "output", callback)
        hook = options["progress_hooks"][0]

        hook({"status": "finished", "filename": "test.mp3"})

        assert len(progress_updates) == 1
        assert progress_updates[0].status == "finished"
        assert progress_updates[0].progress == 100.0

    @pytest.mark.asyncio
    async def test_progress_callback_percent_str(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test progress parsing from percent string."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        options = downloader.get_yt_dlp_options(tmp_path / "output", callback)
        hook = options["progress_hooks"][0]

        hook({
            "status": "downloading",
            "_percent_str": "  75.5%  ",
        })

        assert progress_updates[0].progress == 75.5

    @pytest.mark.asyncio
    async def test_progress_callback_speed_calculation(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test speed calculation from raw value."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        options = downloader.get_yt_dlp_options(tmp_path / "output", callback)
        hook = options["progress_hooks"][0]

        hook({
            "status": "downloading",
            "speed": 1024 * 1024 * 2.5,  # 2.5 MB/s
        })

        assert progress_updates[0].speed == "2.5 MB/s"

    @pytest.mark.asyncio
    async def test_progress_callback_eta_calculation(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        """Test ETA calculation from raw value."""
        progress_updates = []

        def callback(progress: DownloadProgress) -> None:
            progress_updates.append(progress)

        options = downloader.get_yt_dlp_options(tmp_path / "output", callback)
        hook = options["progress_hooks"][0]

        hook({
            "status": "downloading",
            "eta": 90,  # 90 seconds
        })

        assert progress_updates[0].eta == "1m 30s"


# ── 10. Error Handling & Edge Cases ─────────────────────────────────


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_download_error_exception(self) -> None:
        """Test DownloadError exception."""
        error = DownloadError("Test error")
        assert str(error) == "Test error"

    @pytest.mark.asyncio
    async def test_embed_metadata_with_cover_download_failure(
        self, downloader: Downloader, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test metadata embedding when cover download fails."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()

        with patch("mutagen.easyid3.EasyID3") as mock_id3, \
             patch.object(downloader, "_download_cover", return_value=None):

            mock_audio = MagicMock()
            mock_id3.return_value = mock_audio

            # Should complete without error
            await downloader.embed_metadata(file_path, sample_meta)

            # Metadata should still be embedded
            mock_audio.save.assert_called()

    def test_sanitize_filename_dots_and_spaces(self, downloader: Downloader) -> None:
        """Test sanitization of leading/trailing dots and spaces."""
        result = downloader.sanitize_filename("  ...test...  ")
        assert not result.startswith(".")
        assert not result.endswith(".")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_get_output_template_empty_artists(self) -> None:
        """Test template with empty artists list."""
        downloader = Downloader()
        meta = DownloadMeta(title="Song", artist="Artist", artists=[])
        result = downloader.get_output_template(meta)
        assert "Artist" in result

    @pytest.mark.asyncio
    async def test_download_with_nested_directory_in_template(
        self, sample_meta: DownloadMeta, tmp_path: Path
    ) -> None:
        """Test download with nested directory structure."""
        settings = DownloadSettings(
            output_template="{artist}/{album}/{track-number}. {title}"
        )
        downloader = Downloader(settings)

        expected_dir = tmp_path / "Test Artist" / "Test Album"
        output_file = expected_dir / "05. Test Song.mp3"

        with patch.object(Downloader, "_run_yt_dlp"):
            expected_dir.mkdir(parents=True, exist_ok=True)
            output_file.touch()

            result = await downloader.download(
                "https://www.youtube.com/watch?v=test",
                sample_meta,
                tmp_path,
            )

            assert expected_dir.exists()
            assert result == output_file

    def test_get_yt_dlp_options_quality_mappings(self, tmp_path: Path) -> None:
        """Test all quality mapping options."""
        qualities = ["best", "320k", "256k", "192k", "128k"]
        expected = ["0", "320", "256", "192", "128"]

        for quality, expected_value in zip(qualities, expected):
            settings = DownloadSettings(audio_quality=quality)
            downloader = Downloader(settings)
            options = downloader.get_yt_dlp_options(tmp_path / "output")

            extract_audio = next(
                p for p in options["postprocessors"] if p["key"] == "FFmpegExtractAudio"
            )
            assert extract_audio["preferredquality"] == expected_value

    def test_get_yt_dlp_options_format_mappings(self, tmp_path: Path) -> None:
        """Test all format mapping options."""
        formats = {
            "mp3": "mp3",
            "m4a": "m4a",
            "flac": "flac",
            "opus": "opus",
            "ogg": "vorbis",
            "wav": "wav",
        }

        for audio_format, codec in formats.items():
            settings = DownloadSettings(audio_format=audio_format)
            downloader = Downloader(settings)
            options = downloader.get_yt_dlp_options(tmp_path / "output")

            extract_audio = next(
                p for p in options["postprocessors"] if p["key"] == "FFmpegExtractAudio"
            )
            assert extract_audio["preferredcodec"] == codec
