"""Tests for database models."""

import uuid as uuid_mod

import pytest
from datetime import datetime, timezone

from spotdl.db.models.base import generate_uuid, utc_now, GUID


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


class TestGUIDType:
    """Tests for GUID type decorator."""

    def test_process_bind_param_none(self):
        """Test binding None value."""
        guid = GUID()
        result = guid.process_bind_param(None, None)
        assert result is None

    def test_process_bind_param_uuid(self):
        """Test binding UUID value."""
        guid = GUID()
        test_uuid = uuid_mod.uuid4()
        result = guid.process_bind_param(test_uuid, None)
        assert result == str(test_uuid)

    def test_process_bind_param_string(self):
        """Test binding string value."""
        guid = GUID()
        test_str = "12345678-1234-1234-1234-123456789012"
        result = guid.process_bind_param(test_str, None)
        assert result == test_str

    def test_process_result_value_none(self):
        """Test processing None result."""
        guid = GUID()
        result = guid.process_result_value(None, None)
        assert result is None

    def test_process_result_value_uuid(self):
        """Test processing UUID result."""
        guid = GUID()
        test_uuid = uuid_mod.uuid4()
        result = guid.process_result_value(test_uuid, None)
        assert result == test_uuid

    def test_process_result_value_string(self):
        """Test processing string result."""
        guid = GUID()
        test_str = "12345678-1234-1234-1234-123456789012"
        result = guid.process_result_value(test_str, None)
        assert result == uuid_mod.UUID(test_str)


class TestJSONType:
    """Tests for JSONType decorator."""

    def test_process_bind_param_none(self):
        """Test binding None value."""
        from spotdl.db.models.song import JSONType

        json_type = JSONType()

        # Create a mock dialect for SQLite
        class MockDialect:
            name = "sqlite"

        result = json_type.process_bind_param(None, MockDialect())
        assert result is None

    def test_process_bind_param_dict_sqlite(self):
        """Test binding dict value with SQLite."""
        from spotdl.db.models.song import JSONType
        import json

        json_type = JSONType()

        class MockDialect:
            name = "sqlite"

        value = {"key": "value", "list": [1, 2, 3]}
        result = json_type.process_bind_param(value, MockDialect())
        assert result == json.dumps(value)

    def test_process_bind_param_dict_postgresql(self):
        """Test binding dict value with PostgreSQL (passes through)."""
        from spotdl.db.models.song import JSONType

        json_type = JSONType()

        class MockDialect:
            name = "postgresql"

        value = {"key": "value", "list": [1, 2, 3]}
        result = json_type.process_bind_param(value, MockDialect())
        assert result == value  # PostgreSQL passes through

    def test_process_result_value_none(self):
        """Test processing None result."""
        from spotdl.db.models.song import JSONType

        json_type = JSONType()

        class MockDialect:
            name = "sqlite"

        result = json_type.process_result_value(None, MockDialect())
        assert result is None

    def test_process_result_value_string_sqlite(self):
        """Test processing JSON string result with SQLite."""
        from spotdl.db.models.song import JSONType
        import json

        json_type = JSONType()

        class MockDialect:
            name = "sqlite"

        value = {"key": "value", "list": [1, 2, 3]}
        json_str = json.dumps(value)
        result = json_type.process_result_value(json_str, MockDialect())
        assert result == value

    def test_process_result_value_dict_postgresql(self):
        """Test processing dict result with PostgreSQL (passes through)."""
        from spotdl.db.models.song import JSONType

        json_type = JSONType()

        class MockDialect:
            name = "postgresql"

        value = {"key": "value", "list": [1, 2, 3]}
        result = json_type.process_result_value(value, MockDialect())
        assert result == value

    def test_process_result_value_non_string_sqlite(self):
        """Test processing non-string result with SQLite (passes through)."""
        from spotdl.db.models.song import JSONType

        json_type = JSONType()

        class MockDialect:
            name = "sqlite"

        # If value is already a dict (not a string), it should pass through
        value = {"key": "value"}
        result = json_type.process_result_value(value, MockDialect())
        assert result == value

    def test_load_dialect_impl_sqlite(self):
        """Test dialect impl loading for SQLite."""
        from spotdl.db.models.song import JSONType
        from sqlalchemy import Text

        json_type = JSONType()

        class MockTypeDescriptor:
            def __init__(self, type_):
                self.type = type_

        class MockDialect:
            name = "sqlite"

            def type_descriptor(self, type_):
                return MockTypeDescriptor(type_)

        result = json_type.load_dialect_impl(MockDialect())
        assert isinstance(result.type, Text)

    def test_load_dialect_impl_postgresql(self):
        """Test dialect impl loading for PostgreSQL."""
        from spotdl.db.models.song import JSONType
        from sqlalchemy.dialects.postgresql import JSONB

        json_type = JSONType()

        class MockTypeDescriptor:
            def __init__(self, type_):
                self.type = type_

        class MockDialect:
            name = "postgresql"

            def type_descriptor(self, type_):
                return MockTypeDescriptor(type_)

        result = json_type.load_dialect_impl(MockDialect())
        assert isinstance(result.type, JSONB)


class TestGUIDTypeExtended:
    """Extended tests for GUID type decorator with different dialects."""

    def test_load_dialect_impl_postgresql(self):
        """Test dialect impl loading for PostgreSQL."""
        from spotdl.db.models.base import GUID
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID

        guid = GUID()

        class MockTypeDescriptor:
            def __init__(self, type_):
                self.type = type_

        class MockDialect:
            name = "postgresql"

            def type_descriptor(self, type_):
                return MockTypeDescriptor(type_)

        result = guid.load_dialect_impl(MockDialect())
        assert isinstance(result.type, PG_UUID)

    def test_load_dialect_impl_sqlite(self):
        """Test dialect impl loading for SQLite."""
        from spotdl.db.models.base import GUID
        from sqlalchemy import String

        guid = GUID()

        class MockTypeDescriptor:
            def __init__(self, type_):
                self.type = type_

        class MockDialect:
            name = "sqlite"

            def type_descriptor(self, type_):
                return MockTypeDescriptor(type_)

        result = guid.load_dialect_impl(MockDialect())
        assert isinstance(result.type, String)
