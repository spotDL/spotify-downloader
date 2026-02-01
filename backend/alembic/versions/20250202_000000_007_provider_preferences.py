"""Add provider preferences to user_settings

Revision ID: 007_provider_preferences
Revises: 006_data_completeness
Create Date: 2025-02-02

Adds three JSONB columns for ordered provider preferences:
- audio_source_preferences: ordered list of audio source providers
- metadata_source_preferences: ordered list of metadata providers
- lyrics_source_preferences: ordered list of lyrics providers

Each column stores a JSON array of objects with {id, enabled} structure.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_provider_preferences"
down_revision: Union[str, None] = "006_data_completeness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Detect dialect for JSON type
    bind = op.get_bind()
    dialect = bind.dialect.name

    # JSON type: JSONB for PostgreSQL, TEXT for SQLite
    if dialect == "postgresql":
        json_type = postgresql.JSONB
    else:
        json_type = sa.Text

    # Add audio_source_preferences column
    op.add_column(
        "user_settings",
        sa.Column("audio_source_preferences", json_type, nullable=True),
    )

    # Add metadata_source_preferences column
    op.add_column(
        "user_settings",
        sa.Column("metadata_source_preferences", json_type, nullable=True),
    )

    # Add lyrics_source_preferences column
    op.add_column(
        "user_settings",
        sa.Column("lyrics_source_preferences", json_type, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "lyrics_source_preferences")
    op.drop_column("user_settings", "metadata_source_preferences")
    op.drop_column("user_settings", "audio_source_preferences")
