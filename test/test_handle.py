from core import handle

import pytest
import os
import sys


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
        default_config = handle.default_conf['spotify-downloader']
        modified_config = dict(default_config)
        modified_config['file-format'] = 'just_a_test'
        config = handle.merge(default_config, modified_config)
        assert config['file-format'] == modified_config['file-format']


def test_grouped_arguments(tmpdir):
    sys.path[0] = str(tmpdir)
    with pytest.raises(SystemExit):
        handle.get_arguments(to_group=True, to_merge=True)
