"""Config file loading, precedence, and the ``config get|set|edit`` command.

CONTRACT D: platformdirs config file, tomlkit round-trip (comments preserved),
precedence **CLI flag > env (`SPOTDL_*`) > `config.toml` > built-in default**.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit
from spotdl_cli import config as cfgmod
from spotdl_cli.commands.config_cmd import config_app
from spotdl_cli.config import CliConfig, load_config, merge_flag
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def cfg_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point platformdirs at a throwaway config/data home for the test."""
    cdir = tmp_path / "config"
    ddir = tmp_path / "data"
    monkeypatch.setattr(cfgmod.platformdirs, "user_config_dir", lambda *a, **k: str(cdir))
    monkeypatch.setattr(cfgmod.platformdirs, "user_data_dir", lambda *a, **k: str(ddir))
    return cdir


# ---- load_config: file + env merge, precedence -----------------------------


def test_missing_file_yields_defaults(cfg_home: Path) -> None:
    cfg = load_config()
    assert cfg.api_url == cfgmod.DEFAULT_API_URL
    assert cfg.offline is False
    assert cfg.format == "mp3"
    assert cfg.threads == 4


def test_file_values_are_loaded_and_typed(cfg_home: Path) -> None:
    cfg_home.mkdir(parents=True)
    (cfg_home / "config.toml").write_text(
        'api_url = "https://file.example"\nthreads = 8\noffline = true\n'
    )
    cfg = load_config()
    assert cfg.api_url == "https://file.example"
    assert cfg.threads == 8
    assert cfg.offline is True


def test_env_overrides_file(cfg_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_home.mkdir(parents=True)
    (cfg_home / "config.toml").write_text('api_url = "https://file.example"\n')
    monkeypatch.setenv("SPOTDL_API_URL", "https://env.example")
    assert load_config().api_url == "https://env.example"


def test_data_dir_uses_platformdirs(cfg_home: Path, tmp_path: Path) -> None:
    assert cfgmod.data_dir() == tmp_path / "data"


# ---- merge_flag: CLI flag beats the (env-or-file) effective default --------


def test_merge_flag_cli_value_wins() -> None:
    assert merge_flag("cli", config_default="eff") == "cli"


def test_merge_flag_none_defers_to_config_default() -> None:
    # A flag left at its Typer default (None) must not override.
    assert merge_flag(None, config_default="eff") == "eff"


def test_precedence_cli_beats_env_beats_file(
    cfg_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_home.mkdir(parents=True)
    (cfg_home / "config.toml").write_text('api_url = "https://file.example"\n')
    monkeypatch.setenv("SPOTDL_API_URL", "https://env.example")
    effective = load_config().api_url  # env beats file
    assert effective == "https://env.example"
    assert merge_flag("https://cli.example", config_default=effective) == "https://cli.example"


# ---- config get -------------------------------------------------------------


def test_config_get_prints_effective_value(cfg_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTDL_API_URL", "https://env.example")
    result = runner.invoke(config_app, ["get", "api_url"])
    assert result.exit_code == 0
    assert "https://env.example" in result.output


def test_config_get_unknown_key_is_usage_error(cfg_home: Path) -> None:
    result = runner.invoke(config_app, ["get", "not_a_key"])
    assert result.exit_code == 2


def test_config_get_no_key_lists_all(cfg_home: Path) -> None:
    result = runner.invoke(config_app, ["get"])
    assert result.exit_code == 0
    assert "api_url" in result.output
    assert "format" in result.output


# ---- config set: tomlkit round-trip preserves comments/other keys ----------


def test_config_set_preserves_comments_and_other_keys(cfg_home: Path) -> None:
    cfg_home.mkdir(parents=True)
    p = cfg_home / "config.toml"
    p.write_text('# my note\napi_url = "https://old.example"\nformat = "flac"\n')
    result = runner.invoke(config_app, ["set", "api_url", "https://new.example"])
    assert result.exit_code == 0
    text = p.read_text()
    assert "# my note" in text
    assert 'format = "flac"' in text
    doc = tomlkit.parse(text)
    assert doc["api_url"] == "https://new.example"


def test_config_set_creates_file_from_template_when_absent(cfg_home: Path) -> None:
    result = runner.invoke(config_app, ["set", "format", "opus"])
    assert result.exit_code == 0
    p = cfg_home / "config.toml"
    assert p.exists()
    assert tomlkit.parse(p.read_text())["format"] == "opus"


def test_config_set_coerces_typed_values(cfg_home: Path) -> None:
    runner.invoke(config_app, ["set", "threads", "9"])
    runner.invoke(config_app, ["set", "offline", "true"])
    p = cfg_home / "config.toml"
    doc = tomlkit.parse(p.read_text())
    assert doc["threads"] == 9 and isinstance(doc["threads"], int)
    assert doc["offline"] is True
    # And the coerced file round-trips back through the loader.
    cfg = load_config()
    assert cfg.threads == 9 and cfg.offline is True


def test_config_set_unknown_key_is_usage_error(cfg_home: Path) -> None:
    result = runner.invoke(config_app, ["set", "not_a_key", "x"])
    assert result.exit_code == 2
    assert not (cfg_home / "config.toml").exists()


# ---- config edit: invokes $EDITOR, creating a template if absent -----------


def test_config_edit_creates_template_and_invokes_editor(
    cfg_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], *a: object, **k: object) -> object:
        calls["cmd"] = cmd
        return None

    monkeypatch.setenv("EDITOR", "myeditor")
    monkeypatch.setattr(cfgmod.subprocess, "run", fake_run)
    result = runner.invoke(config_app, ["edit"])
    assert result.exit_code == 0
    p = cfg_home / "config.toml"
    assert p.exists()  # created from the commented template
    assert "# spotDL configuration" in p.read_text()
    assert calls["cmd"][0] == "myeditor"
    assert calls["cmd"][1] == str(p)


def test_default_config_template_is_valid_commented_toml() -> None:
    text = cfgmod.default_config_template()
    # Fully commented ⇒ parses to an empty document (all defaults still apply).
    assert tomlkit.parse(text).unwrap() == {}
    assert "api_url" in text


def test_cliconfig_has_all_contract_fields() -> None:
    expected = {
        "api_url",
        "offline",
        "output_dir",
        "output_template",
        "format",
        "bitrate",
        "overwrite",
        "restrict",
        "threads",
        "ffmpeg",
        "ffmpeg_args",
        "ytdlp_args",
        "cookie_file",
        "proxy",
        "embed_lyrics",
        "generate_lrc",
        "sponsor_block",
        "id3_separator",
        "log_level",
    }
    assert expected <= set(CliConfig.model_fields)
