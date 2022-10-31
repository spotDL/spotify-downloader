"""
Web module for the console.
"""

import logging
import sys
import asyncio
import webbrowser

from typing import Dict, Any

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from spotdl.download.downloader import Downloader
from spotdl.download.progress_handler import NAME_TO_LEVEL
from spotdl.utils.github import download_github_dir
from spotdl.utils.config import get_spotdl_path
from spotdl.utils.web import (
    ALLOWED_ORIGINS,
    SPAStaticFiles,
    fix_mime_types,
    app_state,
    get_current_state,
    router,
)
from spotdl._version import __version__


def web(settings: Dict[str, Any]):
    """
    Run the web server.

    ### Arguments
    - settings: Settings dictionary, based on the `SettingsModel` class.
    """

    # Download web app from GitHub
    print("Updating web app")
    web_app_dir = str(get_spotdl_path().absolute())
    download_github_dir(
        "https://github.com/spotdl/web-ui/tree/master/dist",
        output_dir=web_app_dir,
    )

    # Apply the fix for mime types
    fix_mime_types()

    # Set up the app loggers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.propagate = False

    spotipy_logger = logging.getLogger("spotipy")
    spotipy_logger.setLevel(logging.NOTSET)

    # Initialize the web server settings
    app_state.settings = settings
    app_state.logger = uvicorn_logger
    app_state.loop = (
        asyncio.new_event_loop()
        if sys.platform != "win32"
        else asyncio.ProactorEventLoop()  # type: ignore
    )

    app_state.downloader = Downloader(
        audio_providers=settings["audio_providers"],
        lyrics_providers=settings["lyrics_providers"],
        ffmpeg=settings["ffmpeg"],
        bitrate=settings["bitrate"],
        ffmpeg_args=settings["ffmpeg_args"],
        output_format=settings["format"],
        threads=settings["threads"],
        output=settings["output"],
        save_file=settings["save_file"],
        overwrite=settings["overwrite"],
        cookie_file=settings["cookie_file"],
        filter_results=settings["filter_results"],
        search_query=settings["search_query"],
        log_level=settings["log_level"],
        simple_tui=True,
        restrict=settings["restrict"],
        print_errors=settings["print_errors"],
        sponsor_block=settings["sponsor_block"],
        loop=app_state.loop,
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
        allow_origins=ALLOWED_ORIGINS + settings["allowed_origins"]
        if settings["allowed_origins"]
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
        host=settings["host"],
        port=settings["port"],
        workers=1,
        log_level=NAME_TO_LEVEL[settings["log_level"]],
        loop=app_state.loop,  # type: ignore
    )

    app_state.server = Server(config)

    # Open the web browser
    webbrowser.open(f"http://{settings['host']}:{settings['port']}/")

    # Start the web server
    app_state.loop.run_until_complete(app_state.server.serve())
