"""Add blacklisted_tokens table.

Revision ID: 012_token_blacklist
Revises: 011_metadata_embed_preferences
Create Date: 2025-02-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "012_token_blacklist"
down_revision: Union[str, None] = "011_metadata_embed_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create blacklisted_tokens table."""
    op.create_table(
        "blacklisted_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "blacklisted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reason", sa.String(50), nullable=True),
    )

    # Create index for efficient expiry cleanup
    op.create_index(
        "ix_blacklisted_tokens_expires_at",
        "blacklisted_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop blacklisted_tokens table."""
    op.drop_index("ix_blacklisted_tokens_expires_at", table_name="blacklisted_tokens")
    op.drop_table("blacklisted_tokens")
