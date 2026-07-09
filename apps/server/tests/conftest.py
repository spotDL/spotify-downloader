import os

import pytest

# Captured at import time — BEFORE the autouse env-stripping fixture below runs —
# so the Postgres DSN survives the SPOTDL_-prefix scrub. Unset locally (Postgres
# tests skip); CI's `python` job exports it so the dual-dialect migration tests run.
_POSTGRES_URL = os.environ.get("SPOTDL_TEST_POSTGRES_URL")


@pytest.fixture(autouse=True)
def _isolate_spotdl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip SPOTDL_-prefixed env vars so tests relying on Settings() defaults
    are hermetic regardless of the developer's ambient shell environment."""
    for key in list(os.environ):
        if key.startswith("SPOTDL_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def postgres_url() -> str | None:
    """Async Postgres DSN for dual-dialect DB tests, or ``None`` to skip.

    Read from ``SPOTDL_TEST_POSTGRES_URL`` (captured before env isolation). When
    ``None``, Postgres-parametrized cases call ``pytest.skip`` so a developer
    without a Postgres server still gets a fully green ``make check``.
    """
    return _POSTGRES_URL
