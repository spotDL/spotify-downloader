"""
Module which contains the web server related function
FastAPI routes/classes etc.
"""

import argparse
import asyncio
import logging
import mimetypes
import re
import threading
from argparse import Namespace
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope
from uvicorn import Server

from spotdl.download.downloader import Downloader
from spotdl.download.progress_handler import ProgressHandler, SongTracker
from spotdl.types.options import DownloaderOptions, WebOptions
from spotdl.utils.arguments import create_parser
from spotdl.utils.config import DOWNLOADER_OPTIONS, create_settings_type

__all__ = [
    "ALLOWED_ORIGINS",
    "WEB_EDITABLE_SETTINGS",
    "SPAStaticFiles",
    "Client",
    "ApplicationState",
    "app_state",
    "get_current_state",
    "get_client",
    "fix_mime_types",
    "validate_setting",
    "get_settings_changes",
]

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:8800",
    "http://127.0.0.1:8800",
    "https://localhost:8800",
    "https://127.0.0.1:8800",
]

# Settings that clients are allowed to view and change through the web UI.
# Anything else (executable paths, extra yt-dlp/ffmpeg arguments, file paths,
# proxies, ...) can only be set by whoever started the server, because a
# client able to change them could run commands or touch arbitrary files.
WEB_EDITABLE_SETTINGS = {
    "audio_providers",
    "lyrics_providers",
    "genius_token",
    "search_query",
    "filter_results",
    "album_type",
    "only_verified_results",
    "threads",
    "bitrate",
    "format",
    "preload",
    "overwrite",
    "restrict",
    "print_errors",
    "sponsor_block",
    "playlist_numbering",
    "playlist_retain_track_cover",
    "scan_for_songs",
    "fetch_albums",
    "id3_separator",
    "ytm_data",
    "add_unavailable",
    "generate_lrc",
    "force_update_metadata",
    "sync_without_deleting",
    "max_filename_length",
    "detect_formats",
    "redownload",
    "skip_album_art",
    "ignore_albums",
    "skip_explicit",
    "create_skip_file",
    "respect_skip_file",
    "sync_remove_lrc",
}

# Inclusive (min, max) bounds for integer settings, None means unbounded
INT_SETTING_BOUNDS = {
    "threads": (1, 64),
    "max_filename_length": (1, None),
}


def validate_setting(key: str, value: Any, action: argparse.Action) -> Optional[str]:
    """
    Validate a setting value against its command line argument definition.

    ### Arguments
    - key: The setting name.
    - value: The new value.
    - action: The argparse action that defines the setting.

    ### Returns
    - returns an error message, or None if the value is valid.
    """

    if action.choices is not None:
        values = value if action.nargs == "*" else [value]
        if not isinstance(values, list):
            return f"{key} must be a list"

        invalid = [item for item in values if str(item) not in action.choices]
        if invalid:
            return f"Invalid value for {key}: {invalid}"

    if key in INT_SETTING_BOUNDS:
        minimum, maximum = INT_SETTING_BOUNDS[key]
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{key} must be an integer"

        if value < minimum:
            return f"{key} must be at least {minimum}"

        if maximum is not None and value > maximum:
            return f"{key} must be at most {maximum}"

    return None


def get_settings_changes(current: DownloaderOptions, settings: Any) -> Dict[str, Any]:
    """
    Get the setting changes a client is allowed to make.

    ### Arguments
    - current: The client's current settings.
    - settings: The settings sent by the client.

    ### Returns
    - returns the changed settings that are allowed and valid.

    ### Errors
    - ValueError: if the settings aren't a dictionary, or a changed setting
    has an invalid value.
    """

    if not isinstance(settings, dict):
        raise ValueError("Settings must be an object")

    actions = {
        action.dest: action
        for action in create_parser()._actions  # pylint: disable=protected-access
    }

    changes = {}
    for key, value in settings.items():
        # The web UI sends back every setting it received, so unchanged values
        # (including ones it isn't allowed to change) are expected and skipped
        if value is None or value == current.get(key):
            continue

        if key not in WEB_EDITABLE_SETTINGS:
            logger.warning(
                "Ignoring setting that can't be changed from the web UI: %s", key
            )
            continue

        error = validate_setting(key, value, actions[key])
        if error is not None:
            raise ValueError(error)

        changes[key] = value

    return changes


class SPAStaticFiles(StaticFiles):
    """
    Override the static files to serve the index.html and other assets.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        """
        Serve static files from the SPA.

        ### Arguments
        - path: The path to the file.
        - scope: The scope of the request.

        ### Returns
        - returns the response.
        """

        response = await super().get_response(path, scope)
        if response.status_code == 404:
            response = await super().get_response(".", scope)

        response.headers.setdefault(
            "Cache-Control", "max-age=0, no-cache, no-store, , must-revalidate"
        )
        response.headers.setdefault("Pragma", "no-cache")
        response.headers.setdefault("Expires", "0")

        return response


class Client:
    """
    Holds the client's state.
    """

    client_id: str
    downloader: Downloader
    downloader_settings: DownloaderOptions
    disconnect_timer: Optional[threading.Timer] = None
    # update_callback: Optional[Callable] = None
    # update_stack: list[Dict[str, Any]] = []

    def __init__(
        self,
        # websocket: WebSocket,
        client_id: str,
        # update_callback: Optional[Callable] = None,
    ):
        """
        Initialize the WebSocket handler.
        ### Arguments
        - websocket: The WebSocket instance.
        - client_id: The client's ID.
        - downloader_settings: The downloader settings.
        """

        self.downloader_settings = DownloaderOptions(
            **create_settings_type(
                Namespace(config=False),
                dict(app_state.downloader_settings),
                DOWNLOADER_OPTIONS,
            )  # type: ignore
        )

        # self.websocket = websocket
        self.client_id = client_id
        # self.update_callback = update_callback
        self.downloader = self.create_downloader()

        self.disconnect_timer = None

    def create_downloader(self) -> Downloader:
        """
        Create a downloader using the client's settings.

        ### Returns
        - returns the downloader.
        """

        downloader = Downloader(settings=self.downloader_settings, loop=app_state.loop)

        downloader.progress_handler = ProgressHandler(
            simple_tui=True,
            update_callback=self.song_update,
            web_ui=True,
        )

        return downloader

    def update_settings(self, settings: Any) -> DownloaderOptions:
        """
        Apply the settings sent by the client and re-initialize the downloader.
        Only settings in WEB_EDITABLE_SETTINGS can be changed, changes to other
        settings are ignored.

        ### Arguments
        - settings: The settings sent by the client.

        ### Returns
        - returns the new settings.

        ### Errors
        - ValueError: if a changed setting has an invalid value.
        """

        changes = get_settings_changes(self.downloader_settings, settings)

        new_settings = DownloaderOptions(
            **{**self.downloader_settings, **changes}  # type: ignore
        )

        logger.info("Applying settings for client %s: %s", self.client_id, changes)

        self.downloader_settings = new_settings
        self.downloader = self.create_downloader()

        return new_settings

    async def connect(self):
        """
        Called when a new client connects to the websocket.
        """

        # await self.websocket.accept()

        # Add the connection to the list of connections
        if self.disconnect_timer and self.disconnect_timer.is_alive():
            self.disconnect_timer.cancel()
            self.disconnect_timer = None
        app_state.clients[self.client_id] = self
        app_state.logger.info("Client %s connected", self.client_id)

    async def disconnect(self):
        """
        Called when a client disconnects from the websocket.
        """

        # If the disconnect timer is running, cancel it
        if self.disconnect_timer and self.disconnect_timer.is_alive():
            self.disconnect_timer.cancel()

        # Schedule the disconnect now
        app_state.logger.info(
            "Client %s will disconnect in 15 seconds of inactivity", self.client_id
        )
        self.disconnect_timer = threading.Timer(15, self.disconnect_now)
        self.disconnect_timer.start()

    def disconnect_now(self):
        """
        Disconnect the client.
        """
        # Remove the connection from the list of connections
        if self.client_id in app_state.clients:
            # app_state.clients.pop(client_id, None)
            del app_state.clients[self.client_id]
            app_state.logger.info("Client %s disconnected", self.client_id)
        else:
            app_state.logger.warning(
                "Client %s not found on disconnect", self.client_id
            )
        self.disconnect_timer = None

    async def send_update(self, update: Dict[str, Any]):
        """
        Send an update to the client.

        ### Arguments
        - update: The update to send.
        """

        # print(f"Sending update to {self.client_id}: {update}")
        # await self.websocket.send_json(update)
        # self.update_stack.append(update)
        # if self.update_callback:
        #     await self.update_callback(update)

    def song_update(self, progress_handler: SongTracker, message: str):
        """
        Called when a song updates.

        ### Arguments
        - progress_handler: The progress handler.
        - message: The message to send.
        """

        update_message = {
            "song": progress_handler.song.json,
            "progress": progress_handler.progress,
            "message": message,
        }

        asyncio.run_coroutine_threadsafe(
            self.send_update(update_message), app_state.loop
        )

    @classmethod
    def get_instance(cls, client_id: str) -> Optional["Client"]:
        """
        Get the WebSocket instance for a client.

        ### Arguments
        - client_id: The client's ID.

        ### Returns
        - returns the WebSocket instance.
        """

        instance = app_state.clients.get(client_id)
        if instance:
            return instance

        app_state.logger.error("Client %s not found", client_id)

        return None


class ApplicationState:
    """
    Class that holds the application state.
    """

    api: FastAPI
    server: Server
    loop: asyncio.AbstractEventLoop
    web_settings: WebOptions
    downloader_settings: DownloaderOptions
    clients: Dict[str, Client] = {}
    logger: logging.Logger


app_state: ApplicationState = ApplicationState()


def get_current_state() -> ApplicationState:
    """
    Get the current state of the application.

    ### Returns
    - returns the application state.
    """

    return app_state


def get_client(client_id: Union[str, None] = Query(default=None)) -> Client:
    """
    Get the client's state.

    ### Arguments
    - client_id: The client's ID.

    ### Returns
    - returns the client's state.
    """

    if client_id is None:
        raise HTTPException(status_code=400, detail="client_id is required")

    instance = Client.get_instance(client_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="client not found")

    return instance


def fix_mime_types():
    """Fix incorrect entries in the `mimetypes` registry.
    On Windows, the Python standard library's `mimetypes` reads in
    mappings from file extension to MIME type from the Windows
    registry. Other applications can and do write incorrect values
    to this registry, which causes `mimetypes.guess_type` to return
    incorrect values, which causes spotDL to fail to render on
    the frontend.
    This method hard-codes the correct mappings for certain MIME
    types that are known to be either used by TensorBoard or
    problematic in general.
    """

    # Known to be problematic when Visual Studio is installed:
    # https://github.com/tensorflow/tensorboard/issues/3120
    # https://github.com/spotDL/spotify-downloader/issues/1540
    mimetypes.add_type("application/javascript", ".js")

    # Not known to be problematic, but used by spotDL:
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("text/html", ".html")


def validate_search_term(search_term: str) -> bool:
    """
    Validate the search term to check if it is a valid Spotify URL.

    ### Arguments
    - search_term: The search term to validate.

    ### Returns
    - True if the search term is valid, False otherwise.
    """
    search_term = re.sub(r"\/intl-\w+\/", "/", search_term)

    return search_term != "" and (
        "://open.spotify.com/track/" in search_term
        or "://open.spotify.com/album/" in search_term
        or "://open.spotify.com/playlist/" in search_term
        or "://open.spotify.com/artist/" in search_term
    )
