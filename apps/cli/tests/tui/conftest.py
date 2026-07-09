"""Fixtures for the Plan 9 view-model + TUI tests (offline).

Reuses the CLI suite's env isolation (``apps/cli/tests/conftest.py`` autouse) and
adds the fake client, fake credential/config stores, and a wired ``ViewModelFactory``.
"""

from __future__ import annotations

import pytest
from spotdl_cli.config import CliConfig
from spotdl_cli.viewmodels.factory import ViewModelFactory

from .fakes import FakeSpotdlClient


class FakeCredentialStore:
    """In-memory ``CredentialStore`` (token keyed by server origin)."""

    def __init__(self) -> None:
        self.tokens: dict[str, str] = {}
        self.emails: dict[str, str] = {}

    def get_token(self, origin: str) -> str | None:
        return self.tokens.get(origin)

    def store_token(self, origin: str, token: str, email: str) -> None:
        self.tokens[origin] = token
        self.emails[origin] = email

    def delete_token(self, origin: str) -> None:
        self.tokens.pop(origin, None)
        self.emails.pop(origin, None)


class FakeConfigStore:
    """In-memory ``ConfigStore`` over a single ``CliConfig``."""

    def __init__(self, cfg: CliConfig | None = None) -> None:
        self.cfg = cfg if cfg is not None else CliConfig()
        self.saves: list[CliConfig] = []

    def load(self) -> CliConfig:
        return self.cfg

    def save(self, cfg: CliConfig) -> None:
        self.cfg = cfg
        self.saves.append(cfg)


@pytest.fixture
def fake_client() -> FakeSpotdlClient:
    return FakeSpotdlClient()


@pytest.fixture
def fake_creds() -> FakeCredentialStore:
    return FakeCredentialStore()


@pytest.fixture
def fake_store() -> FakeConfigStore:
    return FakeConfigStore()


@pytest.fixture
def vm_factory(
    fake_client: FakeSpotdlClient,
    fake_creds: FakeCredentialStore,
    fake_store: FakeConfigStore,
) -> ViewModelFactory:
    return ViewModelFactory(
        fake_client,
        fake_creds,
        fake_store,
        server_origin="https://api.example.test",
        transport_label="remote · api.example.test",
    )
