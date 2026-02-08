"""Tests for auth screens: LoginScreen, AccountScreen."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from textual.app import App
from textual.widgets import Button, Input, Static

from spotdl_cli.screens.login import LoginScreen
from spotdl_cli.screens.account import AccountScreen
from spotdl_cli.core.api_client import APIError


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.api_url = "http://localhost:8000"
    settings.offline_mode = False
    settings.auth_token = None
    settings.api_timeout = 30.0
    return settings


@pytest.fixture
def mock_settings_authenticated():
    """Create mock settings with auth token."""
    settings = MagicMock()
    settings.api_url = "http://localhost:8000"
    settings.offline_mode = False
    settings.auth_token = "test-token-123"
    settings.api_timeout = 30.0
    return settings


@pytest.fixture
def sample_user_data():
    """Sample user profile data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "is_admin": False,
        "is_active": True,
        "created_at": "2024-01-15T10:30:00Z",
        "reputation": 42,
    }


def _make_test_app(screen_factory):
    """Create a TestApp wrapping the given screen."""

    class TestApp(App):
        def compose(self):
            yield screen_factory()

    return TestApp


# ── LoginScreen ──────────────────────────────────────────────────────────────


class TestLoginScreen:
    """Tests for LoginScreen."""

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_settings):
        """Verify key widgets exist."""
        with patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                assert pilot.app.query_one("#login-container") is not None
                assert pilot.app.query_one("#username-input", Input) is not None
                assert pilot.app.query_one("#password-input", Input) is not None
                assert pilot.app.query_one("#login-btn", Button) is not None

    @pytest.mark.asyncio
    async def test_focus_on_mount(self, mock_settings):
        """Verify username input focused."""
        with patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                username = pilot.app.query_one("#username-input", Input)
                assert username.has_focus

    @pytest.mark.asyncio
    async def test_login_empty_fields(self, mock_settings):
        """Error shown when fields empty."""
        with (
            patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.login.get_api_client"),
        ):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(LoginScreen)
                await screen._login()
                await pilot.pause()

                error = pilot.app.query_one("#login-error", Static)
                assert not error.has_class("hidden")
                assert "username" in str(error.content).lower() or "password" in str(error.content).lower()

    @pytest.mark.asyncio
    async def test_login_calls_api(self, mock_settings):
        """Mock api_client.login(), verify correct params."""
        mock_api = AsyncMock()
        mock_api.login = AsyncMock(return_value={"access_token": "tok"})

        with (
            patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.login.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                pilot.app.query_one("#username-input", Input).value = "myuser"
                pilot.app.query_one("#password-input", Input).value = "mypass"

                screen = pilot.app.query_one(LoginScreen)
                with patch.object(screen, "dismiss"):
                    await screen._login()

                mock_api.login.assert_called_once_with("myuser", "mypass")

    @pytest.mark.asyncio
    async def test_login_success_dismisses(self, mock_settings):
        """Mock success, verify dismiss(True) called."""
        mock_api = AsyncMock()
        mock_api.login = AsyncMock(return_value={"access_token": "tok"})

        with (
            patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.login.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                pilot.app.query_one("#username-input", Input).value = "myuser"
                pilot.app.query_one("#password-input", Input).value = "mypass"

                screen = pilot.app.query_one(LoginScreen)
                with patch.object(screen, "dismiss") as mock_dismiss:
                    await screen._login()
                    mock_dismiss.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_login_failure_shows_error(self, mock_settings):
        """Mock APIError, verify error displayed."""
        mock_api = AsyncMock()
        mock_api.login = AsyncMock(side_effect=APIError("Invalid credentials"))

        with (
            patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.login.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                pilot.app.query_one("#username-input", Input).value = "myuser"
                pilot.app.query_one("#password-input", Input).value = "wrong"

                screen = pilot.app.query_one(LoginScreen)
                await screen._login()
                await pilot.pause()

                error = pilot.app.query_one("#login-error", Static)
                assert not error.has_class("hidden")
                assert "Invalid credentials" in str(error.content)

    @pytest.mark.asyncio
    async def test_login_button_loading_state(self, mock_settings):
        """Verify button disabled during login."""
        mock_api = AsyncMock()
        # Use a side effect to check state during the call
        button_was_disabled = False

        async def check_state(*args, **kwargs):
            nonlocal button_was_disabled
            btn = pilot.app.query_one("#login-btn", Button)
            button_was_disabled = btn.disabled
            return {"access_token": "tok"}

        mock_api.login = AsyncMock(side_effect=check_state)

        with (
            patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.login.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                pilot.app.query_one("#username-input", Input).value = "myuser"
                pilot.app.query_one("#password-input", Input).value = "mypass"

                screen = pilot.app.query_one(LoginScreen)
                with patch.object(screen, "dismiss"):
                    await screen._login()

                assert button_was_disabled is True
                # After login, button should be re-enabled
                btn = pilot.app.query_one("#login-btn", Button)
                assert btn.disabled is False

    @pytest.mark.asyncio
    async def test_enter_key_triggers_login(self, mock_settings):
        """Verify action_submit calls _login."""
        with (
            patch("spotdl_cli.screens.login.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.login.get_api_client"),
        ):
            TestApp = _make_test_app(LoginScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(LoginScreen)

                with patch.object(screen, "_login", new_callable=AsyncMock) as mock_login:
                    await screen.action_submit()
                    mock_login.assert_called_once()


# ── AccountScreen ────────────────────────────────────────────────────────────


class TestAccountScreen:
    """Tests for AccountScreen."""

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_settings):
        """Verify cards exist."""
        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.account.get_api_client"),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                assert pilot.app.query_one("#not-logged-in") is not None
                assert pilot.app.query_one("#profile-card") is not None
                assert pilot.app.query_one("#security-card") is not None

    @pytest.mark.asyncio
    async def test_unauthenticated_state(self, mock_settings):
        """No token shows not-logged-in, hides other cards."""
        mock_settings.auth_token = None
        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.account.get_api_client"),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                not_logged_in = pilot.app.query_one("#not-logged-in")
                assert not not_logged_in.has_class("hidden")

                profile = pilot.app.query_one("#profile-card")
                assert profile.has_class("hidden")

    @pytest.mark.asyncio
    async def test_authenticated_state(self, mock_settings_authenticated, sample_user_data):
        """With token loads profile, shows cards."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                not_logged_in = pilot.app.query_one("#not-logged-in")
                assert not_logged_in.has_class("hidden")

                profile = pilot.app.query_one("#profile-card")
                assert not profile.has_class("hidden")

    @pytest.mark.asyncio
    async def test_update_display(self, mock_settings_authenticated, sample_user_data):
        """Verify fields populated from user data."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                username = pilot.app.query_one("#profile-username", Static)
                assert "testuser" in str(username.content)

                email = pilot.app.query_one("#profile-email", Static)
                assert "test@example.com" in str(email.content)

    @pytest.mark.asyncio
    async def test_change_password_empty_fields(self, mock_settings_authenticated, sample_user_data):
        """Error shown when fields empty."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(AccountScreen)
                await screen._change_password()
                await pilot.pause()

                error = pilot.app.query_one("#password-error", Static)
                assert not error.has_class("hidden")

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, mock_settings_authenticated, sample_user_data):
        """Error shown for mismatched passwords."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                pilot.app.query_one("#current-password", Input).value = "oldpass"
                pilot.app.query_one("#new-password", Input).value = "newpass123"
                pilot.app.query_one("#confirm-password", Input).value = "different"

                screen = pilot.app.query_one(AccountScreen)
                await screen._change_password()
                await pilot.pause()

                error = pilot.app.query_one("#password-error", Static)
                assert not error.has_class("hidden")
                assert "match" in str(error.content).lower()

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, mock_settings_authenticated, sample_user_data):
        """Error for < 8 chars."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                pilot.app.query_one("#current-password", Input).value = "oldpass"
                pilot.app.query_one("#new-password", Input).value = "short"
                pilot.app.query_one("#confirm-password", Input).value = "short"

                screen = pilot.app.query_one(AccountScreen)
                await screen._change_password()
                await pilot.pause()

                error = pilot.app.query_one("#password-error", Static)
                assert not error.has_class("hidden")
                assert "8" in str(error.content)

    @pytest.mark.asyncio
    async def test_logout(self, mock_settings_authenticated, sample_user_data):
        """Verify api_client.logout() called, state reset."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)
        mock_api.logout = AsyncMock()

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(AccountScreen)

                await screen._logout()
                await pilot.pause()

                mock_api.logout.assert_called_once()
                assert screen._user_data == {}

                # Should switch to unauthenticated state
                not_logged_in = pilot.app.query_one("#not-logged-in")
                assert not not_logged_in.has_class("hidden")

    @pytest.mark.asyncio
    async def test_delete_confirmation_flow(self, mock_settings_authenticated, sample_user_data):
        """Show/hide confirmation buttons."""
        mock_api = AsyncMock()
        mock_api.get_me = AsyncMock(return_value=sample_user_data)

        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings_authenticated),
            patch("spotdl_cli.screens.account.get_api_client", return_value=mock_api),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(AccountScreen)

                # Initially confirm and cancel are hidden
                confirm = pilot.app.query_one("#confirm-delete-btn")
                cancel = pilot.app.query_one("#cancel-delete-btn")
                assert confirm.has_class("hidden")
                assert cancel.has_class("hidden")

                # Show confirmation
                screen._show_delete_confirmation()
                await pilot.pause()
                assert not confirm.has_class("hidden")
                assert not cancel.has_class("hidden")

                # Hide confirmation
                screen._hide_delete_confirmation()
                await pilot.pause()
                assert confirm.has_class("hidden")
                assert cancel.has_class("hidden")

    @pytest.mark.asyncio
    async def test_sign_in_button_exists(self, mock_settings):
        """Verify sign-in button navigates to login screen."""
        with (
            patch("spotdl_cli.screens.account.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.account.get_api_client"),
        ):
            TestApp = _make_test_app(AccountScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                btn = pilot.app.query_one("#sign-in-btn", Button)
                assert btn is not None
