"""Add admin fields to Match and User models

Revision ID: 005
Revises: 004
Create Date: 2025-02-01 00:00:01.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status field to matches table for admin moderation
    op.add_column(
        "matches",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index(
        op.f("ix_matches_status"),
        "matches",
        ["status"],
        unique=False,
    )

    # Add last_login to users table
    op.add_column(
        "users",
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove last_login from users
    op.drop_column("users", "last_login")

    # Remove status from matches
    op.drop_index(op.f("ix_matches_status"), table_name="matches")
    op.drop_column("matches", "status")
