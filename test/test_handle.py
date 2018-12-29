import os
import sys
import argparse

from spotdl import handle

import pytest
import yaml


def test_error_m3u_without_list():
    with pytest.raises(SystemExit):
        handle.get_arguments(raw_args=("-s cool song", "--write-m3u"), to_group=True)


def test_m3u_with_list():
    handle.get_arguments(raw_args=("-l cool_list.txt", "--write-m3u"), to_group=True)


def test_log_str_to_int():
    expect_levels = [20, 30, 40, 10]
    levels = [handle.log_leveller(level) for level in handle._LOG_LEVELS_STR]
    assert levels == expect_levels


@pytest.fixture(scope="module")
def config_path_fixture(tmpdir_factory):
    config_path = os.path.join(str(tmpdir_factory.mktemp("config")), "config.yml")
    return config_path


@pytest.fixture(scope="module")
def modified_config_fixture():
    modified_config = dict(handle.default_conf)
    return modified_config


class TestConfig:
    def test_default_config(self, config_path_fixture):
        expect_config = handle.default_conf["spotify-downloader"]
        config = handle.get_config(config_path_fixture)
        assert config == expect_config

    def test_modified_config(self, modified_config_fixture):
        modified_config_fixture["spotify-downloader"]["file-format"] = "just_a_test"
        merged_config = handle.merge(handle.default_conf, modified_config_fixture)
        assert merged_config == modified_config_fixture

    def test_custom_config_path(self, config_path_fixture, modified_config_fixture):
        parser = argparse.ArgumentParser()
        with open(config_path_fixture, "w") as config_file:
            yaml.dump(modified_config_fixture, config_file, default_flow_style=False)
        overridden_config = handle.override_config(
            config_path_fixture, parser, raw_args=""
        )
        modified_values = [
            str(value)
            for value in modified_config_fixture["spotify-downloader"].values()
        ]
        overridden_config.folder = os.path.realpath(overridden_config.folder)
        overridden_values = [
            str(value) for value in overridden_config.__dict__.values()
        ]
        assert sorted(overridden_values) == sorted(modified_values)


def test_grouped_arguments(tmpdir):
    sys.path[0] = str(tmpdir)
    with pytest.raises(SystemExit):
        handle.get_arguments(to_group=True, to_merge=True)
