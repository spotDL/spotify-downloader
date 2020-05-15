import spotdl.config

import argparse
import os
import sys
import yaml
import pytest


@pytest.mark.xfail
@pytest.fixture(scope="module")
def config_path(tmpdir_factory):
    config_path = os.path.join(str(tmpdir_factory.mktemp("config")), "config.yml")
    return config_path


@pytest.mark.xfail
@pytest.fixture(scope="module")
def modified_config():
    modified_config = dict(spotdl.config.DEFAULT_CONFIGURATION)
    return modified_config


def test_dump_n_read_config(config_path):
    expect_config = spotdl.config.DEFAULT_CONFIGURATION
    spotdl.config.dump_config(
        config_path,
        config=expect_config,
    )
    config = spotdl.config.read_config(config_path)
    assert config == expect_config


class TestDefaultConfigFile:
    @pytest.mark.skipif(not sys.platform == "linux", reason="Linux only")
    def test_linux_default_config_file(self):
        expect_default_config_file = os.path.expanduser("~/.config/spotdl/config.yml")
        assert spotdl.config.default_config_file == expect_default_config_file

    @pytest.mark.xfail
    @pytest.mark.skipif(not sys.platform == "darwin" and not sys.platform == "win32",
                        reason="Windows only")
    def test_windows_default_config_file(self):
        raise NotImplementedError

    @pytest.mark.xfail
    @pytest.mark.skipif(not sys.platform == "darwin",
                        reason="OS X only")
    def test_osx_default_config_file(self):
        raise NotImplementedError


class TestConfig:
    def test_default_config(self, config_path):
        expect_config = spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"]
        config = spotdl.config.get_config(config_path)["spotify-downloader"]
        assert config == expect_config

    @pytest.mark.xfail
    def test_custom_config_path(self, config_path, modified_config):
        parser = argparse.ArgumentParser()
        with open(config_path, "w") as config_file:
            yaml.dump(modified_config, config_file, default_flow_style=False)
        overridden_config = spotdl.config.override_config(
            config_path, parser, raw_args=""
        )
        modified_values = [
            str(value)
            for value in modified_config["spotify-downloader"].values()
        ]
        overridden_config.folder = os.path.realpath(overridden_config.folder)
        overridden_values = [
            str(value) for value in overridden_config.__dict__.values()
        ]
        assert sorted(overridden_values) == sorted(modified_values)

