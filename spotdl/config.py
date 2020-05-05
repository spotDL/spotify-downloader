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
        "no_fallback_metadata": False,
        "encoder": "ffmpeg",
        "overwrite": "prompt",
        "quality": "best",
        "input_ext": "automatic",
        "output_ext": "mp3",
        "write_to": None,
        "trim_silence": False,
        "download_only_metadata": False,
        "dry_run": False,
        "music_videos_only": False,
        "no_spaces": False,
        # "processor": "synchronous",
        "output_file": "{artist} - {track-name}.{output-ext}",
        "search_format": "{artist} - {track-name} lyrics",
        "youtube_api_key": None,
        "skip": None,
        "write_successful": None,
        "log_level": "INFO",
        "spotify_client_id": "4fe3fecfe5334023a1472516cc99d805",
        "spotify_client_secret": "0f02b7c483c04257984695007a4a8d5c",
    }
}

default_config_file = os.path.join(
    appdirs.user_config_dir(),
    "spotdl",
    "config.yml"
)

def read_config(config_file):
    with open(config_file, "r") as ymlfile:
        config = yaml.safe_load(ymlfile)
    return config


def dump_config(config_file, config=DEFAULT_CONFIGURATION):
    with open(config_file, "w") as ymlfile:
        yaml.dump(DEFAULT_CONFIGURATION, ymlfile, default_flow_style=False)


def get_config(config_file):
    if os.path.isfile(config_file):
        config = read_config(config_file)
    else:
        config = DEFAULT_CONFIGURATION
        dump_config(config_file, config=DEFAULT_CONFIGURATION)

        logger.info("Writing default configuration to {0}:".format(config_file))

        for line in yaml.dump(
            DEFAULT_CONFIGURATION["spotify-downloader"], default_flow_style=False
        ).split("\n"):
            if line.strip():
                logger.info(line.strip())
        logger.info(
            "Please note that command line arguments have higher priority "
            "than their equivalents in the configuration file"
        )

    return config["spotify-downloader"]

