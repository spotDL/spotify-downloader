"""Reputation system constants and utilities."""

from __future__ import annotations

from enum import IntEnum


class ReputationReward(IntEnum):
    """Reputation point rewards for various actions."""

    # Match submissions
    MATCH_SUBMITTED = 1  # When user submits a match
    MATCH_VERIFIED = 10  # When user's match is verified by admin
    MATCH_REJECTED = -3  # When user's match is rejected

    # Voting
    VOTE_CAST = 1  # When user votes on a match

    # Metadata reports
    REPORT_SUBMITTED = 1  # When user submits a report
    REPORT_FIXED = 5  # When user's report is marked as fixed
    REPORT_REVIEWED = 2  # When user's report is marked as reviewed
    REPORT_DISMISSED = -1  # When user's report is dismissed
