"""Shared provider-test helpers: JSON fixture loading.

Fixtures live under ``tests/providers/fixtures/<provider>/<name>.json`` and are
recorded from real provider responses (see each task's recording step). They are
the source of truth for the pure-parse tests and never touch the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(provider: str, name: str) -> Any:
    path = _FIXTURES / provider / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def load_fixture() -> Any:
    """Return a ``(provider, name) -> parsed JSON`` loader for fixture files."""
    return _load_fixture
