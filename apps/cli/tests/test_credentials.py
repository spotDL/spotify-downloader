"""Credentials store (CONTRACT D): ``credentials.toml``, mode 0600, per-origin.

PATs live in ``<config_dir>/credentials.toml`` — separate from the shared
``config.toml`` — keyed by server origin so several servers can be logged in at
once. The file is always written mode ``0600``.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
from spotdl_cli import config as cfgmod
from spotdl_cli.config import delete_token, get_token, store_token


@pytest.fixture
def cfg_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cdir = tmp_path / "config"
    ddir = tmp_path / "data"
    monkeypatch.setattr(cfgmod.platformdirs, "user_config_dir", lambda *a, **k: str(cdir))
    monkeypatch.setattr(cfgmod.platformdirs, "user_data_dir", lambda *a, **k: str(ddir))
    return cdir


def test_store_then_get_roundtrips(cfg_home: Path) -> None:
    store_token("https://api.spotdl.dev", "spdl_pat_abc", email="u@e.com")
    cred = get_token("https://api.spotdl.dev")
    assert cred is not None
    assert cred.token == "spdl_pat_abc"
    assert cred.email == "u@e.com"


def test_credentials_file_is_mode_0600(cfg_home: Path) -> None:
    store_token("https://api.spotdl.dev", "spdl_pat_abc", email="u@e.com")
    p = cfgmod.credentials_path()
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_second_origin_coexists(cfg_home: Path) -> None:
    store_token("https://api.spotdl.dev", "tok1", email="a@e.com")
    store_token("https://other.example", "tok2", email="b@e.com")
    first = get_token("https://api.spotdl.dev")
    second = get_token("https://other.example")
    assert first is not None and first.token == "tok1"
    assert second is not None and second.token == "tok2"


def test_get_missing_origin_returns_none(cfg_home: Path) -> None:
    assert get_token("https://nope.example") is None


def test_store_overwrites_same_origin(cfg_home: Path) -> None:
    store_token("https://api.spotdl.dev", "old", email="a@e.com")
    store_token("https://api.spotdl.dev", "new", email="a@e.com")
    cred = get_token("https://api.spotdl.dev")
    assert cred is not None and cred.token == "new"


def test_store_records_optional_token_id(cfg_home: Path) -> None:
    store_token("https://api.spotdl.dev", "tok", email="a@e.com", token_id="id-123")
    cred = get_token("https://api.spotdl.dev")
    assert cred is not None and cred.token_id == "id-123"


def test_delete_removes_only_that_origin(cfg_home: Path) -> None:
    store_token("https://api.spotdl.dev", "tok1")
    store_token("https://other.example", "tok2")
    delete_token("https://api.spotdl.dev")
    assert get_token("https://api.spotdl.dev") is None
    kept = get_token("https://other.example")
    assert kept is not None and kept.token == "tok2"
    # File remains mode 0600 after a rewrite.
    assert stat.S_IMODE(cfgmod.credentials_path().stat().st_mode) == 0o600


def test_delete_missing_origin_is_noop(cfg_home: Path) -> None:
    delete_token("https://nope.example")  # must not raise
    assert get_token("https://nope.example") is None
