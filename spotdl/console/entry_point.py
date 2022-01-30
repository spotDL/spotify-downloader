import sys
import json
import signal
import logging

from spotdl.console.save import save
from spotdl.download import Downloader
from spotdl.console.preload import preload
from spotdl.console.download import download
from spotdl.utils.config import DEFAULT_CONFIG
from spotdl.utils.ffmpeg import download_ffmpeg
from spotdl.utils.config import get_config_file
from spotdl.utils.version import check_for_updates
from spotdl.utils.arguments import parse_arguments
from spotdl.utils.spotify import SpotifyClient, SpotifyError
from spotdl.download.downloader import DownloaderError


def console_entry_point():
    """
    Console entry point for spotdl. This is where the magic happens.
    """

    # Don't log too much
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("spotipy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Download ffmpeg if the `--download-ffmpeg` flag is passed
    # This is done before the argument parser so it doesn't require `operation`
    # and `query` to be passed. Exit after downloading ffmpeg
    if "--download-ffmpeg" in sys.argv:
        download_ffmpeg()

        return None

    # Generate the config file if it doesn't exist
    # or overwrite the current config file if the `--overwrite-config` flag is passed
    # This is done before the argument parser so it doesn't requires `operation`
    # and `query` to be passed. exit after downloading ffmpeg
    if "--generate-config" in sys.argv:
        config_path = get_config_file()
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=4)

        return None

    # Get information about the current version and display it
    # Exit after displaying the version
    if "--check-for-updates" in sys.argv:
        check_for_updates()

        return None

    # Parse the arguments
    arguments = parse_arguments()

    # Get the config file
    config = {}
    if arguments.config:
        # Load the config file
        with open(get_config_file(), "r", encoding="utf-8") as config_file:
            config = json.load(config_file)

    # Create settings dict
    # Settings from config file will override the ones from the command line
    settings = {}
    for key in DEFAULT_CONFIG:
        if config.get(key) is None:
            settings[key] = arguments.__dict__[key]
        else:
            settings[key] = config[key]

    # Don't log too much when running web ui
    if arguments.operation == "web":
        settings["log_level"] = "CRITICAL"

    if arguments.query and "saved" in arguments.query and not settings["user_auth"]:
        raise SpotifyError("You must be logged in to use the saved query.")

    # Initialize spotify client
    SpotifyClient.init(
        client_id=settings["client_id"],
        client_secret=settings["client_secret"],
        user_auth=settings["user_auth"],
        cache_path=settings["cache_path"],
        no_cache=settings["no_cache"],
    )

    if arguments.operation in ["download", "preload"]:
        # Initialize the downloader
        # for download, load and preload operations
        downloader = Downloader(
            audio_provider=settings["audio_provider"],
            lyrics_provider=settings["lyrics_provider"],
            ffmpeg=settings["ffmpeg"],
            variable_bitrate=settings["variable_bitrate"],
            constant_bitrate=settings["constant_bitrate"],
            ffmpeg_args=settings["ffmpeg_args"],
            output_format=settings["format"],
            save_file=settings["save_file"],
            threads=settings["threads"],
            output=settings["output"],
            overwrite=settings["overwrite"],
            search_query=settings["search_query"],
            cookie_file=settings["cookie_file"],
            log_level=settings["log_level"],
            simple_tui=settings["simple_tui"],
        )

        def graceful_exit(_signal, _frame):
            downloader.progress_handler.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, graceful_exit)
        signal.signal(signal.SIGTERM, graceful_exit)

        if arguments.operation == "preload":
            if not settings["save_file"].endswith(".spotdl"):
                raise DownloaderError("Save file has to end with .spotdl")

        if arguments.operation == "download":
            download(arguments.query, downloader=downloader, m3u_file=settings["m3u"])
        elif arguments.operation == "preload":
            preload(
                query=arguments.query,
                save_path=settings["save_file"],
                downloader=downloader,
            )

        downloader.progress_handler.close()
    elif arguments.operation == "save":
        # Save the songs to a file
        save(
            query=arguments.query,
            save_path=settings["save_file"],
            threads=settings["threads"],
        )
    elif arguments.operation == "web":
        try:
            from spotdl.console.web import (  # pylint: disable=C0415,C0410,W0707,W0611
                web,
            )
        except ModuleNotFoundError as exception:
            raise Exception(
                "To use the web interface, you need to install web package with"
                "`pip install spotdl[web]`"
            ) from exception

        web(settings)

    return None
