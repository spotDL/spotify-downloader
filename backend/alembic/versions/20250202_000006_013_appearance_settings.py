"""Add appearance settings to user_settings.

Revision ID: 013_appearance_settings
Revises: 012_token_blacklist
Create Date: 2025-02-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "013_appearance_settings"
down_revision: Union[str, None] = "012_token_blacklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add appearance settings columns to user_settings."""
    op.add_column(
        "user_settings",
        sa.Column("compact_sidebar", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "user_settings",
        sa.Column("enable_animations", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "user_settings",
        sa.Column("reduce_motion", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove appearance settings columns from user_settings."""
    op.drop_column("user_settings", "reduce_motion")
    op.drop_column("user_settings", "enable_animations")
    op.drop_column("user_settings", "compact_sidebar")
