import os
import sys
import argparse

from spotdl import handle
from spotdl import const

import pytest
import yaml


def test_log_str_to_int():
    expect_levels = [20, 30, 40, 10]
    levels = [handle.log_leveller(level)
              for level in handle._LOG_LEVELS_STR]
    assert levels == expect_levels


class TestConfig:
    def test_default_config(self, tmpdir):
        expect_config = handle.default_conf['spotify-downloader']
        global config_path
        config_path = os.path.join(str(tmpdir), 'config.yml')
        config = handle.get_config(config_path)
        assert config == expect_config

    def test_modified_config(self):
        global modified_config
        modified_config = dict(handle.default_conf)
        modified_config['spotify-downloader']['file-format'] = 'just_a_test'
        merged_config = handle.merge(handle.default_conf, modified_config)
        assert merged_config == modified_config

    def test_custom_config_path(self, tmpdir):
        parser = argparse.ArgumentParser()
        with open(config_path, 'w') as config_file:
            yaml.dump(modified_config, config_file, default_flow_style=False)
        overridden_config = handle.override_config(config_path,
                                                   parser,
                                                   raw_args='')
        modified_values = [ str(value) for value in modified_config['spotify-downloader'].values() ]
        overridden_config.folder = os.path.realpath(overridden_config.folder)
        overridden_values = [ str(value) for value in overridden_config.__dict__.values() ]
        assert sorted(overridden_values) == sorted(modified_values)


def test_grouped_arguments(tmpdir):
    sys.path[0] = str(tmpdir)
    with pytest.raises(SystemExit):
        handle.get_arguments(to_group=True, to_merge=True)
