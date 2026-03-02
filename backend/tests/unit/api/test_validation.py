"""Tests for API validation utilities."""

import pytest
from fastapi import HTTPException

from spotdl.api.v1.validation import (
    validate_isrc,
    validate_pagination,
    validate_url,
    validate_uuid,
)


class TestValidateUUID:
    """Tests for validate_uuid function."""

    def test_validate_uuid_valid(self):
        """Test validation of valid UUID."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(valid_uuid)
        assert str(result) == valid_uuid

    def test_validate_uuid_valid_mixed_case(self):
        """Test validation of valid UUID with mixed case."""
        valid_uuid = "550E8400-E29B-41D4-A716-446655440000"
        result = validate_uuid(valid_uuid)
        assert str(result).lower() == valid_uuid.lower()

    def test_validate_uuid_invalid_format(self):
        """Test validation of invalid UUID format."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("not-a-uuid")
        assert exc_info.value.status_code == 400
        assert "not a valid UUID format" in exc_info.value.detail

    def test_validate_uuid_empty_string(self):
        """Test validation of empty string."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("")
        assert exc_info.value.status_code == 400

    def test_validate_uuid_custom_field_name(self):
        """Test validation with custom field name in error message."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("invalid", field_name="Song ID")
        assert "Song ID" in exc_info.value.detail


class TestValidateURL:
    """Tests for validate_url function."""

    def test_validate_url_http(self):
        """Test validation of HTTP URL."""
        url = "http://example.com"
        result = validate_url(url)
        assert result == url

    def test_validate_url_https(self):
        """Test validation of HTTPS URL."""
        url = "https://example.com/path"
        result = validate_url(url)
        assert result == url

    def test_validate_url_with_port(self):
        """Test validation of URL with port."""
        url = "https://example.com:8080/path"
        result = validate_url(url)
        assert result == url

    def test_validate_url_localhost(self):
        """Test validation of localhost URL."""
        url = "http://localhost:3000"
        result = validate_url(url)
        assert result == url

    def test_validate_url_ip_address(self):
        """Test validation of IP address URL."""
        url = "http://192.168.1.1:8000"
        result = validate_url(url)
        assert result == url

    def test_validate_url_invalid_format(self):
        """Test validation of invalid URL format."""
        with pytest.raises(HTTPException) as exc_info:
            validate_url("not a url")
        assert exc_info.value.status_code == 400
        assert "Invalid URL format" in exc_info.value.detail

    def test_validate_url_missing_protocol(self):
        """Test validation of URL without protocol."""
        with pytest.raises(HTTPException) as exc_info:
            validate_url("example.com")
        assert exc_info.value.status_code == 400

    def test_validate_url_allowed_domains_match(self):
        """Test validation with allowed domains - matching domain."""
        url = "https://open.spotify.com/track/123"
        result = validate_url(url, allowed_domains=["spotify.com"])
        assert result == url

    def test_validate_url_allowed_domains_subdomain(self):
        """Test validation with allowed domains - subdomain match."""
        url = "https://api.example.com/endpoint"
        result = validate_url(url, allowed_domains=["example.com"])
        assert result == url

    def test_validate_url_allowed_domains_exact_match(self):
        """Test validation with allowed domains - exact match."""
        url = "https://example.com/path"
        result = validate_url(url, allowed_domains=["example.com"])
        assert result == url

    def test_validate_url_allowed_domains_not_allowed(self):
        """Test validation with allowed domains - domain not allowed."""
        with pytest.raises(HTTPException) as exc_info:
            validate_url(
                "https://notallowed.com/path", allowed_domains=["spotify.com", "youtube.com"]
            )
        assert exc_info.value.status_code == 400
        assert "URL domain not allowed" in exc_info.value.detail
        assert "spotify.com" in exc_info.value.detail

    def test_validate_url_allowed_domains_with_port(self):
        """Test validation with allowed domains and port in URL."""
        url = "https://example.com:8080/path"
        result = validate_url(url, allowed_domains=["example.com"])
        assert result == url


class TestValidatePagination:
    """Tests for validate_pagination function."""

    def test_validate_pagination_valid(self):
        """Test validation of valid pagination parameters."""
        skip, limit = validate_pagination(0, 10)
        assert skip == 0
        assert limit == 10

    def test_validate_pagination_max_limit(self):
        """Test validation at max limit."""
        skip, limit = validate_pagination(0, 100)
        assert skip == 0
        assert limit == 100

    def test_validate_pagination_custom_max_limit(self):
        """Test validation with custom max limit."""
        skip, limit = validate_pagination(10, 50, max_limit=50)
        assert skip == 10
        assert limit == 50

    def test_validate_pagination_negative_skip(self):
        """Test validation with negative skip."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination(-1, 10)
        assert exc_info.value.status_code == 400
        assert "non-negative" in exc_info.value.detail

    def test_validate_pagination_zero_limit(self):
        """Test validation with zero limit."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination(0, 0)
        assert exc_info.value.status_code == 400
        assert "at least 1" in exc_info.value.detail

    def test_validate_pagination_negative_limit(self):
        """Test validation with negative limit."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination(0, -5)
        assert exc_info.value.status_code == 400
        assert "at least 1" in exc_info.value.detail

    def test_validate_pagination_limit_exceeds_max(self):
        """Test validation with limit exceeding max."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination(0, 101)
        assert exc_info.value.status_code == 400
        assert "cannot exceed 100" in exc_info.value.detail

    def test_validate_pagination_custom_max_exceeded(self):
        """Test validation with custom max limit exceeded."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination(0, 51, max_limit=50)
        assert exc_info.value.status_code == 400
        assert "cannot exceed 50" in exc_info.value.detail


class TestValidateISRC:
    """Tests for validate_isrc function."""

    def test_validate_isrc_valid(self):
        """Test validation of valid ISRC."""
        isrc = "USRC17607839"
        result = validate_isrc(isrc)
        assert result == "USRC17607839"

    def test_validate_isrc_valid_lowercase(self):
        """Test validation of valid ISRC in lowercase."""
        isrc = "usrc17607839"
        result = validate_isrc(isrc)
        assert result == "USRC17607839"

    def test_validate_isrc_with_hyphens(self):
        """Test validation of ISRC with hyphens."""
        isrc = "US-RC1-76-07839"
        result = validate_isrc(isrc)
        assert result == "USRC17607839"

    def test_validate_isrc_standard_format(self):
        """Test validation of standard ISRC format."""
        isrc = "GB-AJY-12-34567"
        result = validate_isrc(isrc)
        assert result == "GBAJY1234567"

    def test_validate_isrc_too_short(self):
        """Test validation of ISRC that's too short."""
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc("US12345")
        assert exc_info.value.status_code == 400
        assert "must be 12 characters" in exc_info.value.detail

    def test_validate_isrc_too_long(self):
        """Test validation of ISRC that's too long."""
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc("USRC176078391234")
        assert exc_info.value.status_code == 400
        assert "must be 12 characters" in exc_info.value.detail

    def test_validate_isrc_invalid_country_code(self):
        """Test validation of ISRC with invalid country code (digits)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc("12RC17607839")
        assert exc_info.value.status_code == 400
        assert "Invalid ISRC format" in exc_info.value.detail

    def test_validate_isrc_invalid_format_letters_in_year(self):
        """Test validation of ISRC with letters in year position."""
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc("USRC1AB07839")
        assert exc_info.value.status_code == 400
        assert "Invalid ISRC format" in exc_info.value.detail

    def test_validate_isrc_invalid_format_letters_in_designation(self):
        """Test validation of ISRC with letters in designation code."""
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc("USRC1760ABC9")
        assert exc_info.value.status_code == 400
        assert "Invalid ISRC format" in exc_info.value.detail

    def test_validate_isrc_empty_string(self):
        """Test validation of empty ISRC."""
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc("")
        assert exc_info.value.status_code == 400
        assert "must be 12 characters" in exc_info.value.detail

    def test_validate_isrc_with_spaces(self):
        """Test validation of ISRC with spaces."""
        isrc = "US RC1 76 07839"
        # Spaces are not removed, only hyphens
        with pytest.raises(HTTPException) as exc_info:
            validate_isrc(isrc)
        assert exc_info.value.status_code == 400
