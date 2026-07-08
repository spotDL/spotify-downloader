import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_spotdl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip SPOTDL_-prefixed env vars so tests relying on Settings() defaults
    are hermetic regardless of the developer's ambient shell environment."""
    for key in list(os.environ):
        if key.startswith("SPOTDL_"):
            monkeypatch.delenv(key, raising=False)
