"""Tests for security module."""

import pytest
from datetime import timedelta

from spotdl.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self) -> None:
        """Test get_password_hash returns a string."""
        hashed = get_password_hash("test_password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_for_same_input(self) -> None:
        """Test get_password_hash generates different hashes (due to salt)."""
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Test verify_password returns True for correct password."""
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test verify_password returns False for incorrect password."""
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_password(self) -> None:
        """Test verify_password with empty password."""
        hashed = get_password_hash("test")
        assert verify_password("", hashed) is False

    def test_hash_password_special_characters(self) -> None:
        """Test hashing password with special characters."""
        password = "test!@#$%^&*()_+"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_unicode(self) -> None:
        """Test hashing password with unicode characters."""
        password = "test_пароль_密码"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestAccessToken:
    """Tests for access token functions."""

    def test_create_access_token_returns_string(self) -> None:
        """Test create_access_token returns a string."""
        token = create_access_token("user123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_is_jwt(self) -> None:
        """Test created token is valid JWT format."""
        token = create_access_token("user123")
        assert isinstance(token, str)
        # JWT has 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_access_token_valid(self) -> None:
        """Test decoding valid access token."""
        user_id = "user123"
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload.sub == user_id

    def test_decode_access_token_invalid(self) -> None:
        """Test decoding invalid token returns None."""
        invalid_token = "invalid.token.here"
        result = decode_token(invalid_token)
        assert result is None

    def test_decode_access_token_empty(self) -> None:
        """Test decoding empty token returns None."""
        result = decode_token("")
        assert result is None

    def test_decode_access_token_malformed(self) -> None:
        """Test decoding malformed token returns None."""
        result = decode_token("not.a.jwt")
        assert result is None

    def test_create_and_decode_token_roundtrip(self) -> None:
        """Test creating and decoding token works round-trip."""
        user_id = "test_user_456"
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload.sub == user_id

    def test_token_contains_expected_structure(self) -> None:
        """Test token has JWT structure (3 parts)."""
        token = create_access_token("user123")
        parts = token.split(".")
        assert len(parts) == 3  # JWT has header, payload, signature
