"""Add metadata_embed_preferences column to user_settings.

Revision ID: 011_metadata_embed_preferences
Revises: 010_comprehensive_metadata
Create Date: 2025-02-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "011_metadata_embed_preferences"
down_revision: Union[str, None] = "010_comprehensive_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metadata_embed_preferences column."""
    # Add metadata_embed_preferences column to user_settings
    # This stores per-field source priority for metadata embedding
    # Format: {
    #   "default_order": ["spotify", "musicbrainz", "discogs"],
    #   "fields": {
    #     "genres": {"order": ["musicbrainz", "discogs"], "enabled": true},
    #     ...
    #   }
    # }
    op.add_column(
        "user_settings",
        sa.Column("metadata_embed_preferences", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove metadata_embed_preferences column."""
    op.drop_column("user_settings", "metadata_embed_preferences")
