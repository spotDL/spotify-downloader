"""
Web module for the console.
"""

import asyncio
import logging
import os
import sys
import webbrowser
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from spotdl._version import __version__
from spotdl.types.options import DownloaderOptions, WebOptions
from spotdl.utils.config import get_web_ui_path
from spotdl.utils.github import download_github_dir
from spotdl.utils.logging import NAME_TO_LEVEL
from spotdl.utils.web import (
    ALLOWED_ORIGINS,
    SPAStaticFiles,
    app_state,
    fix_mime_types,
    get_current_state,
    router,
)

__all__ = ["web"]

logger = logging.getLogger(__name__)


def web(web_settings: WebOptions, downloader_settings: DownloaderOptions):
    """
    Run the web server.

    ### Arguments
    - web_settings: Web server settings.
    - downloader_settings: Downloader settings.
    """

    # Apply the fix for mime types
    fix_mime_types()

    # Set up the app loggers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.propagate = False

    spotipy_logger = logging.getLogger("spotipy")
    spotipy_logger.setLevel(logging.NOTSET)

    # Initialize the web server settings
    app_state.web_settings = web_settings
    app_state.logger = uvicorn_logger

    # Create the event loop
    app_state.loop = (
        asyncio.new_event_loop()
        if sys.platform != "win32"
        else asyncio.ProactorEventLoop()  # type: ignore
    )

    downloader_settings["simple_tui"] = True

    # Download web app from GitHub if not already downloaded or force flag set
    web_app_dir = get_web_ui_path()
    dist_dir = web_app_dir / "dist"
    if (not dist_dir.exists() or web_settings["force_update_gui"]) and web_settings[
        "web_gui_location"
    ] is None:
        if web_settings["web_gui_repo"] is None:
            gui_repo = "https://github.com/spotdl/web-ui/tree/master/dist"
        else:
            gui_repo = web_settings["web_gui_repo"]

        logger.info("Updating web app from %s", gui_repo)

        download_github_dir(
            gui_repo,
            output_dir=str(web_app_dir),
        )
        web_app_dir = Path(os.path.join(web_app_dir, "dist")).resolve()
    elif web_settings["web_gui_location"]:
        web_app_dir = Path(web_settings["web_gui_location"]).resolve()
        logger.info("Using custom web app location: %s", web_app_dir)
    else:
        logger.info(
            "Using cached web app. To update use the `--force-update-gui` flag."
        )
        web_app_dir = Path(os.path.join(web_app_dir, "dist")).resolve()

    app_state.api = FastAPI(
        title="spotDL",
        description="Download music from Spotify",
        version=__version__,
        dependencies=[Depends(get_current_state)],
    )

    app_state.api.include_router(router)

    # Add the CORS middleware
    app_state.api.add_middleware(
        CORSMiddleware,
        allow_origins=(
            ALLOWED_ORIGINS + web_settings["allowed_origins"]
            if web_settings["allowed_origins"]
            else ALLOWED_ORIGINS
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add the static files
    app_state.api.mount(
        "/",
        SPAStaticFiles(directory=web_app_dir, html=True),
        name="static",
    )
    protocol = "http"
    config = Config(
        app=app_state.api,
        host=web_settings["host"],
        port=web_settings["port"],
        workers=1,
        log_level=NAME_TO_LEVEL[downloader_settings["log_level"]],
        loop=app_state.loop,  # type: ignore
    )
    if web_settings["enable_tls"]:
        logger.info("Enabeling TLS")
        protocol = "https"
        config.ssl_certfile = web_settings["cert_file"]
        config.ssl_keyfile = web_settings["key_file"]
        config.ssl_ca_certs = web_settings["ca_file"]

    app_state.server = Server(config)

    app_state.downloader_settings = downloader_settings

    # Open the web browser
    webbrowser.open(f"{protocol}://{web_settings['host']}:{web_settings['port']}/")

    if not web_settings["web_use_output_dir"]:
        logger.info(
            "Files are stored in temporary directory "
            "and will be deleted after the program exits "
            "to save them to current directory permanently "
            "enable the `web_use_output_dir` option "
        )
    else:
        logger.info(
            "Files are stored in current directory "
            "to save them to temporary directory "
            "disable the `web_use_output_dir` option "
        )

    logger.info("Starting web server \n")

    # Start the web server
    app_state.loop.run_until_complete(app_state.server.serve())
