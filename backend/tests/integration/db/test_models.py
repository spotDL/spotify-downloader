"""Tests for database models."""

import pytest
from datetime import datetime, timezone

from spotdl.db.models.base import generate_uuid, utc_now


class TestBaseHelpers:
    """Tests for base model helper functions."""

    def test_generate_uuid(self):
        """Test UUID generation."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        # Should be valid UUIDs
        assert uuid1 is not None
        assert uuid2 is not None

        # Should be unique
        assert uuid1 != uuid2

    def test_utc_now(self):
        """Test UTC timestamp generation."""
        now = utc_now()

        assert now is not None
        assert now.tzinfo == timezone.utc

        # Should be close to current time
        diff = abs((datetime.now(timezone.utc) - now).total_seconds())
        assert diff < 1.0
