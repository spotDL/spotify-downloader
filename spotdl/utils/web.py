"""
Module which contains the web server related function
FastAPI routes/classes etc.
"""


import asyncio
import logging
import os
from typing import Dict, Any, List, Optional

import mimetypes

from starlette.types import Scope
from uvicorn import Server
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import (
    Response,
    FastAPI,
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from spotdl.download.progress_handler import NAME_TO_LEVEL, ProgressHandler, SongTracker

from spotdl.types.song import Song
from spotdl.download.downloader import Downloader
from spotdl.utils.search import get_search_results
from spotdl.utils.config import get_spotdl_path
from spotdl._version import __version__

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

        return response


class WSProgressHandler:
    """
    Handles song updates.
    """

    def __init__(self, websocket: WebSocket, client_id: str):
        """
        Initialize the WebSocket handler.
        ### Arguments
        - websocket: The WebSocket instance.
        - client_id: The client's ID.
        """

        self.websocket = websocket
        self.client_id = client_id

    async def connect(self):
        """
        Called when a new client connects to the websocket.
        """

        await self.websocket.accept()

        # Add the connection to the list of connections
        app_state.ws_instances.append(self)

        app_state.logger.info("Client %s connected", self.client_id)

    async def send_update(self, update: Dict[str, Any]):
        """
        Send an update to the client.

        ### Arguments
        - update: The update to send.
        """

        await self.websocket.send_json(update)

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
    def get_instance(cls, client_id: str) -> Optional["WSProgressHandler"]:
        """
        Get the WebSocket instance for a client.

        ### Arguments
        - client_id: The client's ID.

        ### Returns
        - returns the WebSocket instance.
        """

        for instance in app_state.ws_instances:
            if instance.client_id == client_id:
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
    downloader: Downloader
    settings: Dict[str, Any]
    ws_instances: List[WSProgressHandler] = []
    logger: logging.Logger


router = APIRouter()
app_state: ApplicationState = ApplicationState()


def get_current_state() -> ApplicationState:
    """
    Get the current state of the application.

    ### Returns
    - returns the application state.
    """

    return app_state


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Websocket endpoint.
    ### Arguments
    - websocket: The WebSocket instance.
    """

    await WSProgressHandler(websocket, client_id).connect()

    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        instance = WSProgressHandler.get_instance(client_id)
        if instance:
            app_state.ws_instances.remove(instance)

        if (
            len(app_state.ws_instances) == 0
            and app_state.settings["keep_alive"] is False
        ):
            app_state.logger.debug(
                "No active connections, waiting 1s before shutting down"
            )

            await asyncio.sleep(1)

            # Wait 5 seconds before shutting down
            # This is to prevent the server from shutting down when a client
            # disconnects and reconnects quickly (e.g. when refreshing the page)
            if len(app_state.ws_instances) == 0:
                # Perform a clean exit
                app_state.logger.info("Shutting down server, no active connections")
                app_state.server.force_exit = True
                app_state.server.should_exit = True
                await app_state.server.shutdown()


@router.get("/api/song/url")
def song_from_url(url: str) -> Song:
    """
    Search for a song on spotify using url.

    ### Arguments
    - url: The url to search.

    ### Returns
    - returns the first result as a Song object.
    """

    return Song.from_url(url)


@router.get("/api/songs/search")
def query_search(query: str) -> List[Song]:
    """
    Parse search term and return list of Song objects.

    ### Arguments
    - query: The query to parse.

    ### Returns
    - returns a list of Song objects.
    """

    return get_search_results(query)


@router.post("/api/download/url")
async def download_url(
    url: str, client_id: str, state: ApplicationState = Depends(get_current_state)
) -> Optional[str]:
    """
    Download songs using Song url.

    ### Arguments
    - url: The url to download.

    ### Returns
    - returns the file path if the song was downloaded.
    """

    state.downloader.output = str(
        (get_spotdl_path() / f"web/sessions/{client_id}").absolute()
    )

    ws_instance = WSProgressHandler.get_instance(client_id)
    if ws_instance is not None:
        state.downloader.progress_handler = ProgressHandler(
            NAME_TO_LEVEL[state.settings["log_level"]],
            simple_tui=True,
            update_callback=ws_instance.song_update,
        )

    try:
        # Fetch song metadata
        song = Song.from_url(url)

        # Download Song
        _, path = await state.downloader.pool_download(song)

        if path is None:
            state.logger.error(f"Failure downloading {song.name}")

            raise HTTPException(
                status_code=500, detail=f"Error downloading: {song.name}"
            )

        # Strip Filename
        filename = os.path.basename(path)

        return filename

    except Exception as exception:
        state.logger.error(f"Error downloading! {exception}")

        raise HTTPException(
            status_code=500, detail=f"Error downloading: {exception}"
        ) from exception


@router.get("/api/download/file")
async def download_file(file: str) -> FileResponse:
    """
    Download file using path.

    ### Arguments
    - file: The file path.

    ### Returns
    - returns the file response, filename specified to return as attachment.
    """

    return FileResponse(
        str((get_spotdl_path() / f"web/sessions/{file}").absolute()),
        filename=file,
    )


@router.get("/api/settings")
def get_settings(
    state: ApplicationState = Depends(get_current_state),
) -> Dict[str, Any]:
    """
    Get the settings.

    ### Returns
    - returns the settings.
    """

    return state.settings


@router.post("/api/settings/update")
def update_settings(
    settings: Dict[str, Any], state: ApplicationState = Depends(get_current_state)
) -> Dict[str, Any]:
    """
    Change downloader settings by re-initializing the downloader.

    ### Arguments
    - settings: The settings to change.

    ### Returns
    - returns True if the settings were changed.
    """

    # Create shallow copy of settings
    settings_cpy = state.settings.copy()

    # Update settings with new settings that are not None
    settings_cpy.update({k: v for k, v in settings.items() if v is not None})

    state.logger.info(f"Applying settings: {settings_cpy}")

    # Re-initialize downloader
    state.downloader = Downloader(
        audio_providers=settings_cpy["audio_providers"],
        lyrics_providers=settings_cpy["lyrics_providers"],
        ffmpeg=settings_cpy["ffmpeg"],
        bitrate=settings_cpy["bitrate"],
        ffmpeg_args=settings_cpy["ffmpeg_args"],
        output_format=settings_cpy["format"],
        threads=settings_cpy["threads"],
        output=settings_cpy["output"],
        save_file=settings_cpy["save_file"],
        overwrite=settings_cpy["overwrite"],
        cookie_file=settings_cpy["cookie_file"],
        filter_results=settings_cpy["filter_results"],
        search_query=settings_cpy["search_query"],
        log_level=settings_cpy["log_level"],
        simple_tui=True,
        restrict=settings_cpy["restrict"],
        print_errors=settings_cpy["print_errors"],
        sponsor_block=settings_cpy["sponsor_block"],
        loop=state.loop,
    )

    return settings_cpy


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
    # <https://github.com/tensorflow/tensorboard/issues/3120>
    # https://github.com/spotDL/spotify-downloader/issues/1540
    mimetypes.add_type("application/javascript", ".js")

    # Not known to be problematic, but used by spotDL:
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("text/html", ".html")
