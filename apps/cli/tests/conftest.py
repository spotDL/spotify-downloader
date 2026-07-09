"""Shared pytest fixtures for the ``spotdl_cli`` suite.

Mirrors the server suite's env isolation: strip ``SPOTDL_``-prefixed
environment variables so a developer's real config never leaks into a test run
(the embedded ``Settings`` the CLI builds read the same ``SPOTDL_`` prefix).
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_spotdl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip ``SPOTDL_``-prefixed env vars so tests relying on ``Settings()``
    defaults are hermetic regardless of the developer's ambient shell."""
    for key in list(os.environ):
        if key.startswith("SPOTDL_"):
            monkeypatch.delenv(key, raising=False)
