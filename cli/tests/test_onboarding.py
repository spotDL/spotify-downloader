"""Tests for onboarding screen."""

import pytest
from pathlib import Path
from unittest.mock import patch

from spotdl_cli.screens.onboarding import should_show_onboarding, OnboardingScreen
from spotdl_cli.config import get_settings


class TestShouldShowOnboarding:
    """Tests for should_show_onboarding function."""

    def test_should_show_when_marker_missing(self, tmp_path: Path) -> None:
        """Test that onboarding shows when marker file is missing."""
        with patch("spotdl_cli.screens.onboarding.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.config_dir = tmp_path
            # No marker file exists
            assert should_show_onboarding() is True

    def test_should_not_show_when_marker_exists(self, tmp_path: Path) -> None:
        """Test that onboarding doesn't show when marker exists."""
        with patch("spotdl_cli.screens.onboarding.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.config_dir = tmp_path
            # Create marker file
            marker = tmp_path / ".onboarding_complete"
            marker.touch()
            assert should_show_onboarding() is False


class TestOnboardingScreen:
    """Tests for OnboardingScreen."""

    def test_screen_init(self) -> None:
        """Test screen initialization."""
        screen = OnboardingScreen()
        assert screen._step == 0
        assert screen._total_steps == 4

    def test_mark_onboarding_complete(self, tmp_path: Path) -> None:
        """Test marking onboarding as complete."""
        screen = OnboardingScreen()

        with patch.object(screen._settings, "config_dir", tmp_path):
            screen._mark_onboarding_complete()
            marker = tmp_path / ".onboarding_complete"
            assert marker.exists()
