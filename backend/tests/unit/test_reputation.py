"""Tests for reputation module."""

from spotdl.core.reputation import ReputationReward


class TestReputationReward:
    """Tests for ReputationReward enum."""

    def test_reputation_reward_enum_values(self) -> None:
        """Test ReputationReward enum has expected values."""
        assert hasattr(ReputationReward, "MATCH_SUBMITTED")
        assert hasattr(ReputationReward, "MATCH_VERIFIED")
        assert hasattr(ReputationReward, "MATCH_REJECTED")
        assert hasattr(ReputationReward, "VOTE_CAST")
        assert hasattr(ReputationReward, "REPORT_SUBMITTED")
        assert hasattr(ReputationReward, "REPORT_FIXED")
        assert hasattr(ReputationReward, "REPORT_REVIEWED")
        assert hasattr(ReputationReward, "REPORT_DISMISSED")

    def test_reputation_reward_values(self) -> None:
        """Test ReputationReward enum values are correct."""
        assert ReputationReward.MATCH_SUBMITTED.value == 1
        assert ReputationReward.MATCH_VERIFIED.value == 10
        assert ReputationReward.MATCH_REJECTED.value == -3
        assert ReputationReward.VOTE_CAST.value == 1
        assert ReputationReward.REPORT_SUBMITTED.value == 1
        assert ReputationReward.REPORT_FIXED.value == 5
        assert ReputationReward.REPORT_REVIEWED.value == 2
        assert ReputationReward.REPORT_DISMISSED.value == -1

    def test_reputation_reward_positive_actions(self) -> None:
        """Test positive reputation actions have positive values."""
        assert ReputationReward.MATCH_SUBMITTED.value > 0
        assert ReputationReward.MATCH_VERIFIED.value > 0
        assert ReputationReward.VOTE_CAST.value > 0
        assert ReputationReward.REPORT_SUBMITTED.value > 0
        assert ReputationReward.REPORT_FIXED.value > 0
        assert ReputationReward.REPORT_REVIEWED.value > 0

    def test_reputation_reward_negative_actions(self) -> None:
        """Test negative reputation actions have negative values."""
        assert ReputationReward.MATCH_REJECTED.value < 0
        assert ReputationReward.REPORT_DISMISSED.value < 0

    def test_reputation_reward_match_verified_highest(self) -> None:
        """Test MATCH_VERIFIED has highest reward value."""
        all_rewards = [r.value for r in ReputationReward]
        assert ReputationReward.MATCH_VERIFIED.value == max(all_rewards)

    def test_reputation_reward_match_rejected_lowest(self) -> None:
        """Test MATCH_REJECTED has lowest reward value."""
        all_rewards = [r.value for r in ReputationReward]
        assert ReputationReward.MATCH_REJECTED.value == min(all_rewards)
