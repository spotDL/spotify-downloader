"""
Web module for the console.
"""

import asyncio
import logging
import sys
import webbrowser

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from spotdl._version import __version__
from spotdl.types.options import DownloaderOptions, WebOptions
from spotdl.utils.config import get_spotdl_path
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

    # Download web app from GitHub
    logger.info("Updating web app \n")
    web_app_dir = str(get_spotdl_path().absolute())
    download_github_dir(
        "https://github.com/spotdl/web-ui/tree/dev/dist",
        output_dir=web_app_dir,
    )

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
        allow_origins=ALLOWED_ORIGINS + web_settings["allowed_origins"]
        if web_settings["allowed_origins"]
        else ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add the static files
    app_state.api.mount(
        "/",
        SPAStaticFiles(directory=web_app_dir + "/dist", html=True),
        name="static",
    )

    config = Config(
        app=app_state.api,
        host=web_settings["host"],
        port=web_settings["port"],
        workers=1,
        log_level=NAME_TO_LEVEL[downloader_settings["log_level"]],
        loop=app_state.loop,  # type: ignore
    )

    app_state.server = Server(config)

    app_state.downloader_settings = downloader_settings

    # Open the web browser
    webbrowser.open(f"http://{web_settings['host']}:{web_settings['port']}/")

    # Start the web server
    app_state.loop.run_until_complete(app_state.server.serve())
