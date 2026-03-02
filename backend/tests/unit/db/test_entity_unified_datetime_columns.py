"""Regression tests for unified entity timezone-aware datetime columns."""

from sqlalchemy import DateTime

from spotdl.db.models.entity_unified import EntitySnapshot


def test_entity_snapshot_datetime_columns_are_timezone_aware():
    fetched_type = EntitySnapshot.__table__.c.fetched_at.type
    expires_type = EntitySnapshot.__table__.c.expires_at.type

    assert isinstance(fetched_type, DateTime)
    assert fetched_type.timezone is True
    assert isinstance(expires_type, DateTime)
    assert expires_type.timezone is True
