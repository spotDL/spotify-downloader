import appdirs
import yaml
import os

import spotdl.util
import logging
logger = logging.getLogger(__name__)

DEFAULT_CONFIGURATION = {
    "spotify-downloader": {
        "manual": False,
        "no_metadata": False,
        "no_encode": False,
        "overwrite": "prompt",
        "quality": "best",
        "input_ext": "automatic",
        "output_ext": "mp3",
        "write_to": None,
        "trim_silence": False,
        "search_format": "{artist} - {track-name} lyrics",
        "dry_run": False,
        "no_spaces": False,
        # "processor": "synchronous",
        "output_file": "{artist} - {track-name}.{output-ext}",
        "skip_file": None,
        "write_successful_file": None,
        "spotify_client_id": "4fe3fecfe5334023a1472516cc99d805",
        "spotify_client_secret": "0f02b7c483c04257984695007a4a8d5c",
        "log_level": "INFO",
    }
}

DEFAULT_CONFIG_FILE = os.path.join(
    appdirs.user_config_dir(),
    "spotdl",
    "config.yml"
)

def read_config(config_file):
    with open(config_file, "r") as ymlfile:
        config = yaml.safe_load(ymlfile)
    return config


def dump_config(config_file=None, config=DEFAULT_CONFIGURATION):
    if config_file is None:
        config = yaml.dump(config, default_flow_style=False)
        return config

    with open(config_file, "w") as ymlfile:
        yaml.dump(config, ymlfile, default_flow_style=False)

