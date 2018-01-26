from core import handle

import pytest
import os


def test_log_str_to_int():
    expect_levels = [20, 30, 40, 10]
    levels = [handle.log_leveller(level)
              for level in handle._LOG_LEVELS_STR]
    assert levels == expect_levels


def test_default_config(tmpdir):
    expect_config = handle.default_conf['spotify-downloader']
    config_path = os.path.join(tmpdir, 'config.yml')
    config = handle.get_config(config_path)
    assert config == expect_config


def test_arguments():
    with pytest.raises(SystemExit):
        handle.get_arguments(to_group=True, to_merge=True)
