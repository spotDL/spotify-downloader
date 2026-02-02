"""Tests for query parsing utilities."""

import pytest

from spotdl_cli.core.query import (
    QUERY_PREFIXES,
    SPECIAL_KEYWORDS,
    QueryType,
    extract_content_type_from_url,
    extract_platform_from_url,
    is_url,
    parse_query,
)


class TestParseQuery:
    """Tests for parse_query function."""

    def test_empty_query(self) -> None:
        """Test parsing empty query."""
        query_type, value = parse_query("")
        assert query_type == QueryType.AUTO
        assert value == ""

    def test_whitespace_query(self) -> None:
        """Test parsing whitespace-only query."""
        query_type, value = parse_query("   ")
        assert query_type == QueryType.AUTO
        assert value == ""

    def test_album_prefix(self) -> None:
        """Test parsing album: prefix."""
        query_type, value = parse_query("album:Random Access Memories")
        assert query_type == QueryType.ALBUM
        assert value == "Random Access Memories"

    def test_album_prefix_case_insensitive(self) -> None:
        """Test album prefix is case insensitive."""
        query_type, value = parse_query("ALBUM:Discovery")
        assert query_type == QueryType.ALBUM
        assert value == "Discovery"

    def test_album_prefix_with_extra_spaces(self) -> None:
        """Test album prefix with extra spaces."""
        query_type, value = parse_query("album:  The Dark Side of the Moon  ")
        assert query_type == QueryType.ALBUM
        assert value == "The Dark Side of the Moon"

    def test_artist_prefix(self) -> None:
        """Test parsing artist: prefix."""
        query_type, value = parse_query("artist:Daft Punk")
        assert query_type == QueryType.ARTIST
        assert value == "Daft Punk"

    def test_artist_prefix_case_insensitive(self) -> None:
        """Test artist prefix is case insensitive."""
        query_type, value = parse_query("ARTIST:The Beatles")
        assert query_type == QueryType.ARTIST
        assert value == "The Beatles"

    def test_playlist_prefix(self) -> None:
        """Test parsing playlist: prefix."""
        query_type, value = parse_query("playlist:My Favorites")
        assert query_type == QueryType.PLAYLIST
        assert value == "My Favorites"

    def test_playlist_prefix_case_insensitive(self) -> None:
        """Test playlist prefix is case insensitive."""
        query_type, value = parse_query("Playlist:Workout Mix")
        assert query_type == QueryType.PLAYLIST
        assert value == "Workout Mix"

    def test_track_prefix(self) -> None:
        """Test parsing track: prefix."""
        query_type, value = parse_query("track:Around the World")
        assert query_type == QueryType.TRACK
        assert value == "Around the World"

    def test_track_prefix_case_insensitive(self) -> None:
        """Test track prefix is case insensitive."""
        query_type, value = parse_query("TRACK:Bohemian Rhapsody")
        assert query_type == QueryType.TRACK
        assert value == "Bohemian Rhapsody"

    def test_saved_keyword(self) -> None:
        """Test parsing 'saved' keyword."""
        query_type, value = parse_query("saved")
        assert query_type == QueryType.SAVED
        assert value == ""

    def test_saved_keyword_case_insensitive(self) -> None:
        """Test 'saved' keyword is case insensitive."""
        query_type, value = parse_query("SAVED")
        assert query_type == QueryType.SAVED
        assert value == ""

    def test_all_user_playlists_keyword(self) -> None:
        """Test parsing 'all-user-playlists' keyword."""
        query_type, value = parse_query("all-user-playlists")
        assert query_type == QueryType.USER_PLAYLISTS
        assert value == ""

    def test_all_user_playlists_case_insensitive(self) -> None:
        """Test 'all-user-playlists' is case insensitive."""
        query_type, value = parse_query("ALL-USER-PLAYLISTS")
        assert query_type == QueryType.USER_PLAYLISTS
        assert value == ""

    def test_all_user_saved_albums_keyword(self) -> None:
        """Test parsing 'all-user-saved-albums' keyword."""
        query_type, value = parse_query("all-user-saved-albums")
        assert query_type == QueryType.SAVED_ALBUMS
        assert value == ""

    def test_spotify_url_http(self) -> None:
        """Test parsing Spotify HTTP URL."""
        url = "https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_spotify_url_no_protocol(self) -> None:
        """Test parsing Spotify URL without protocol."""
        url = "open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_spotify_uri(self) -> None:
        """Test parsing Spotify URI."""
        uri = "spotify:track:4PTG3Z6ehGkBFwjybzWkR8"
        query_type, value = parse_query(uri)
        assert query_type == QueryType.URL
        assert value == uri

    def test_deezer_url(self) -> None:
        """Test parsing Deezer URL."""
        url = "https://www.deezer.com/track/123456"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_youtube_url(self) -> None:
        """Test parsing YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_youtube_short_url(self) -> None:
        """Test parsing YouTube short URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_youtube_music_url(self) -> None:
        """Test parsing YouTube Music URL."""
        url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_soundcloud_url(self) -> None:
        """Test parsing SoundCloud URL."""
        url = "https://soundcloud.com/artist/track"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_bandcamp_url(self) -> None:
        """Test parsing Bandcamp URL."""
        url = "https://artist.bandcamp.com/track/song"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_apple_music_url(self) -> None:
        """Test parsing Apple Music URL."""
        url = "https://music.apple.com/us/album/random-access-memories/617154241"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_tidal_url(self) -> None:
        """Test parsing Tidal URL."""
        url = "https://tidal.com/browse/track/123456"
        query_type, value = parse_query(url)
        assert query_type == QueryType.URL
        assert value == url

    def test_plain_search_query(self) -> None:
        """Test parsing plain search query."""
        query_type, value = parse_query("Daft Punk")
        assert query_type == QueryType.AUTO
        assert value == "Daft Punk"

    def test_search_query_with_special_chars(self) -> None:
        """Test parsing search query with special characters."""
        query_type, value = parse_query("Rock & Roll (2021 Remaster)")
        assert query_type == QueryType.AUTO
        assert value == "Rock & Roll (2021 Remaster)"

    def test_query_with_leading_trailing_spaces(self) -> None:
        """Test query with leading/trailing spaces is trimmed."""
        query_type, value = parse_query("  Daft Punk  ")
        assert query_type == QueryType.AUTO
        assert value == "Daft Punk"


class TestIsUrl:
    """Tests for is_url function."""

    def test_http_url(self) -> None:
        """Test HTTP URL is recognized."""
        assert is_url("http://example.com") is True

    def test_https_url(self) -> None:
        """Test HTTPS URL is recognized."""
        assert is_url("https://example.com") is True

    def test_spotify_url(self) -> None:
        """Test Spotify URL is recognized."""
        assert is_url("https://open.spotify.com/track/123") is True

    def test_spotify_uri(self) -> None:
        """Test Spotify URI is recognized."""
        assert is_url("spotify:track:123") is True

    def test_deezer_url(self) -> None:
        """Test Deezer URL is recognized."""
        assert is_url("https://deezer.com/track/123") is True

    def test_youtube_url(self) -> None:
        """Test YouTube URL is recognized."""
        assert is_url("https://youtube.com/watch?v=abc") is True

    def test_youtube_short_url(self) -> None:
        """Test YouTube short URL is recognized."""
        assert is_url("https://youtu.be/abc") is True

    def test_plain_text_not_url(self) -> None:
        """Test plain text is not recognized as URL."""
        assert is_url("Daft Punk") is False

    def test_prefix_not_url(self) -> None:
        """Test prefix is not recognized as URL."""
        assert is_url("album:Discovery") is False

    def test_case_insensitive(self) -> None:
        """Test URL detection is case insensitive."""
        assert is_url("HTTPS://SPOTIFY.COM/track/123") is True

    def test_with_whitespace(self) -> None:
        """Test URL detection with whitespace."""
        assert is_url("  https://spotify.com/track/123  ") is True


class TestExtractPlatformFromUrl:
    """Tests for extract_platform_from_url function."""

    def test_spotify_url(self) -> None:
        """Test extracting platform from Spotify URL."""
        platform = extract_platform_from_url(
            "https://open.spotify.com/track/123"
        )
        assert platform == "spotify"

    def test_spotify_uri(self) -> None:
        """Test extracting platform from Spotify URI."""
        platform = extract_platform_from_url("spotify:track:123")
        assert platform == "spotify"

    def test_deezer_url(self) -> None:
        """Test extracting platform from Deezer URL."""
        platform = extract_platform_from_url("https://www.deezer.com/track/123")
        assert platform == "deezer"

    def test_youtube_url(self) -> None:
        """Test extracting platform from YouTube URL."""
        platform = extract_platform_from_url(
            "https://www.youtube.com/watch?v=abc"
        )
        assert platform == "youtube"

    def test_youtube_short_url(self) -> None:
        """Test extracting platform from YouTube short URL."""
        platform = extract_platform_from_url("https://youtu.be/abc")
        assert platform == "youtube"

    def test_youtube_music_url(self) -> None:
        """Test extracting platform from YouTube Music URL."""
        platform = extract_platform_from_url(
            "https://music.youtube.com/watch?v=abc"
        )
        assert platform == "youtube_music"

    def test_soundcloud_url(self) -> None:
        """Test extracting platform from SoundCloud URL."""
        platform = extract_platform_from_url("https://soundcloud.com/artist/track")
        assert platform == "soundcloud"

    def test_bandcamp_url(self) -> None:
        """Test extracting platform from Bandcamp URL."""
        platform = extract_platform_from_url(
            "https://artist.bandcamp.com/track/song"
        )
        assert platform == "bandcamp"

    def test_apple_music_url(self) -> None:
        """Test extracting platform from Apple Music URL."""
        platform = extract_platform_from_url(
            "https://music.apple.com/us/album/test/123"
        )
        assert platform == "apple_music"

    def test_tidal_url(self) -> None:
        """Test extracting platform from Tidal URL."""
        platform = extract_platform_from_url("https://tidal.com/browse/track/123")
        assert platform == "tidal"

    def test_unknown_url(self) -> None:
        """Test extracting platform from unknown URL."""
        platform = extract_platform_from_url("https://example.com/track/123")
        assert platform is None

    def test_case_insensitive(self) -> None:
        """Test platform extraction is case insensitive."""
        platform = extract_platform_from_url(
            "HTTPS://OPEN.SPOTIFY.COM/TRACK/123"
        )
        assert platform == "spotify"


class TestExtractContentTypeFromUrl:
    """Tests for extract_content_type_from_url function."""

    # Spotify URLs
    def test_spotify_track_url(self) -> None:
        """Test extracting track type from Spotify URL."""
        content_type = extract_content_type_from_url(
            "https://open.spotify.com/track/123"
        )
        assert content_type == "track"

    def test_spotify_track_uri(self) -> None:
        """Test extracting track type from Spotify URI."""
        content_type = extract_content_type_from_url("spotify:track:123")
        assert content_type == "track"

    def test_spotify_album_url(self) -> None:
        """Test extracting album type from Spotify URL."""
        content_type = extract_content_type_from_url(
            "https://open.spotify.com/album/123"
        )
        assert content_type == "album"

    def test_spotify_album_uri(self) -> None:
        """Test extracting album type from Spotify URI."""
        content_type = extract_content_type_from_url("spotify:album:123")
        assert content_type == "album"

    def test_spotify_artist_url(self) -> None:
        """Test extracting artist type from Spotify URL."""
        content_type = extract_content_type_from_url(
            "https://open.spotify.com/artist/123"
        )
        assert content_type == "artist"

    def test_spotify_artist_uri(self) -> None:
        """Test extracting artist type from Spotify URI."""
        content_type = extract_content_type_from_url("spotify:artist:123")
        assert content_type == "artist"

    def test_spotify_playlist_url(self) -> None:
        """Test extracting playlist type from Spotify URL."""
        content_type = extract_content_type_from_url(
            "https://open.spotify.com/playlist/123"
        )
        assert content_type == "playlist"

    def test_spotify_playlist_uri(self) -> None:
        """Test extracting playlist type from Spotify URI."""
        content_type = extract_content_type_from_url("spotify:playlist:123")
        assert content_type == "playlist"

    # Deezer URLs
    def test_deezer_track_url(self) -> None:
        """Test extracting track type from Deezer URL."""
        content_type = extract_content_type_from_url(
            "https://www.deezer.com/track/123"
        )
        assert content_type == "track"

    def test_deezer_album_url(self) -> None:
        """Test extracting album type from Deezer URL."""
        content_type = extract_content_type_from_url(
            "https://www.deezer.com/album/123"
        )
        assert content_type == "album"

    def test_deezer_artist_url(self) -> None:
        """Test extracting artist type from Deezer URL."""
        content_type = extract_content_type_from_url(
            "https://www.deezer.com/artist/123"
        )
        assert content_type == "artist"

    def test_deezer_playlist_url(self) -> None:
        """Test extracting playlist type from Deezer URL."""
        content_type = extract_content_type_from_url(
            "https://www.deezer.com/playlist/123"
        )
        assert content_type == "playlist"

    # YouTube URLs
    def test_youtube_video_url(self) -> None:
        """Test extracting track type from YouTube video URL."""
        content_type = extract_content_type_from_url(
            "https://www.youtube.com/watch?v=abc"
        )
        assert content_type == "track"

    def test_youtube_playlist_url(self) -> None:
        """Test extracting playlist type from YouTube playlist URL."""
        content_type = extract_content_type_from_url(
            "https://www.youtube.com/playlist?list=PLabc"
        )
        assert content_type == "playlist"

    def test_youtube_video_with_list_param(self) -> None:
        """Test YouTube video URL with list parameter."""
        content_type = extract_content_type_from_url(
            "https://www.youtube.com/watch?v=abc&list=PLdef"
        )
        assert content_type == "playlist"

    def test_youtube_short_url(self) -> None:
        """Test extracting type from YouTube short URL."""
        content_type = extract_content_type_from_url("https://youtu.be/abc")
        assert content_type == "track"

    # SoundCloud URLs
    def test_soundcloud_track_url(self) -> None:
        """Test extracting track type from SoundCloud URL."""
        content_type = extract_content_type_from_url(
            "https://soundcloud.com/artist/track-name"
        )
        assert content_type == "track"

    def test_soundcloud_set_url(self) -> None:
        """Test extracting playlist type from SoundCloud set URL."""
        content_type = extract_content_type_from_url(
            "https://soundcloud.com/artist/sets/playlist-name"
        )
        assert content_type == "playlist"

    # Apple Music URLs
    def test_apple_music_album_url(self) -> None:
        """Test extracting album type from Apple Music URL."""
        content_type = extract_content_type_from_url(
            "https://music.apple.com/us/album/test/123"
        )
        assert content_type == "album"

    def test_apple_music_artist_url(self) -> None:
        """Test extracting artist type from Apple Music URL."""
        content_type = extract_content_type_from_url(
            "https://music.apple.com/us/artist/test/123"
        )
        assert content_type == "artist"

    def test_apple_music_playlist_url(self) -> None:
        """Test extracting playlist type from Apple Music URL."""
        content_type = extract_content_type_from_url(
            "https://music.apple.com/us/playlist/test/123"
        )
        assert content_type == "playlist"

    def test_apple_music_song_url(self) -> None:
        """Test extracting track type from Apple Music song URL."""
        content_type = extract_content_type_from_url(
            "https://music.apple.com/us/song/test/123"
        )
        # Should default to track for Apple Music URLs without specific pattern
        assert content_type == "track"

    # Unknown URLs
    def test_unknown_url(self) -> None:
        """Test extracting content type from unknown URL."""
        content_type = extract_content_type_from_url("https://example.com/page")
        assert content_type is None

    def test_case_insensitive(self) -> None:
        """Test content type extraction is case insensitive."""
        content_type = extract_content_type_from_url(
            "HTTPS://OPEN.SPOTIFY.COM/TRACK/123"
        )
        assert content_type == "track"


class TestQueryConstants:
    """Tests for query constants."""

    def test_query_prefixes_contains_expected(self) -> None:
        """Test QUERY_PREFIXES contains expected values."""
        assert "album:" in QUERY_PREFIXES
        assert "artist:" in QUERY_PREFIXES
        assert "playlist:" in QUERY_PREFIXES
        assert "track:" in QUERY_PREFIXES

    def test_special_keywords_contains_expected(self) -> None:
        """Test SPECIAL_KEYWORDS contains expected values."""
        assert "saved" in SPECIAL_KEYWORDS
        assert "all-user-playlists" in SPECIAL_KEYWORDS
        assert "all-user-saved-albums" in SPECIAL_KEYWORDS


class TestQueryType:
    """Tests for QueryType enum."""

    def test_auto_value(self) -> None:
        """Test AUTO value."""
        assert QueryType.AUTO == "auto"

    def test_url_value(self) -> None:
        """Test URL value."""
        assert QueryType.URL == "url"

    def test_album_value(self) -> None:
        """Test ALBUM value."""
        assert QueryType.ALBUM == "album"

    def test_artist_value(self) -> None:
        """Test ARTIST value."""
        assert QueryType.ARTIST == "artist"

    def test_playlist_value(self) -> None:
        """Test PLAYLIST value."""
        assert QueryType.PLAYLIST == "playlist"

    def test_track_value(self) -> None:
        """Test TRACK value."""
        assert QueryType.TRACK == "track"

    def test_saved_value(self) -> None:
        """Test SAVED value."""
        assert QueryType.SAVED == "saved"

    def test_user_playlists_value(self) -> None:
        """Test USER_PLAYLISTS value."""
        assert QueryType.USER_PLAYLISTS == "user_playlists"

    def test_saved_albums_value(self) -> None:
        """Test SAVED_ALBUMS value."""
        assert QueryType.SAVED_ALBUMS == "saved_albums"
