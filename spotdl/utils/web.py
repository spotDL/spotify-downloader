"""
Module which contains the web server related function
FastAPI routes/classes etc.
"""

import asyncio
import logging
import mimetypes
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
from spotdl.utils.config import DOWNLOADER_OPTIONS, create_settings_type

__all__ = [
    "ALLOWED_ORIGINS",
    "SPAStaticFiles",
    "Client",
    "ApplicationState",
    "app_state",
    "get_current_state",
    "get_client",
    "fix_mime_types",
]

ALLOWED_ORIGINS = [
    "http://localhost:8800",
    "http://127.0.0.1:8800",
    "https://localhost:8800",
    "https://127.0.0.1:8800",
]


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
        self.downloader = Downloader(
            settings=self.downloader_settings, loop=app_state.loop
        )

        self.downloader.progress_handler = ProgressHandler(
            simple_tui=True,
            update_callback=self.song_update,
            web_ui=True,
        )

        self.disconnect_timer = None

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
    return search_term != "" and (
        "://open.spotify.com/track/" in search_term
        or "://open.spotify.com/album/" in search_term
        or "://open.spotify.com/playlist/" in search_term
        or "://open.spotify.com/artist/" in search_term
    )
