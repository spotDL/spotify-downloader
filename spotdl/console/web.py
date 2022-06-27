"""
Web module for the console.
"""

import asyncio
import logging
import os
import json
import webbrowser

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

import mimetypes


from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # pylint: disable=E0611
from uvicorn import Config, Server
from starlette.types import Scope

import nest_asyncio

from spotdl.download.downloader import Downloader, DownloaderError
from spotdl.download.progress_handler import NAME_TO_LEVEL, ProgressHandler, SongTracker
from spotdl.types.song import Song
from spotdl.utils.github import download_github_dir
from spotdl.utils.search import parse_query
from spotdl.utils.search import get_search_results
from spotdl.utils.config import get_spotdl_path


ALLOWED_ORIGINS = [
    "http://localhost:8800",
    "https://127.0.0.1:8800",
    "http://localhost:3000",
    "http://localhost:8080",
    "*",
]


class App:
    """
    App class that holds the application state.
    """

    server: Any
    downloader: Downloader
    settings: Dict[str, Any]
    loop: asyncio.AbstractEventLoop


class SongModel(BaseModel):
    """
    A song object used for types and validation.
    We can't use the Song class directly because FastAPI doesn't support dataclasses.
    """

    name: str
    artists: List[str]
    artist: str
    album_name: str
    album_artist: str
    genres: List[str]
    disc_number: int
    disc_count: int
    copyright: str
    duration: int
    year: int
    date: str
    track_number: int
    tracks_count: int
    isrc: str
    song_id: str
    cover_url: Optional[str]
    explicit: bool
    publisher: str
    url: str
    download_url: Optional[str] = None


class SettingsModel(BaseModel):
    """
    A settings object used for types and validation.
    """

    log_level: Optional[str]
    cache_path: Optional[str]
    audio_providers: Optional[List[str]]
    lyrics_providers: Optional[List[str]]
    ffmpeg: Optional[str]
    variable_bitrate: Optional[int]
    constant_bitrate: Optional[int]
    ffmpeg_args: Optional[List[str]]
    format: Optional[str]
    save_file: Optional[str]
    m3u: Optional[str]
    output: Optional[str]
    overwrite: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    user_auth: Optional[bool]
    threads: Optional[int]


app = App()
app.server = FastAPI()
app.server.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nest_asyncio.apply()


class WSProgressHandler:
    """
    Handles all the WebSocket connections.
    """

    instances: List["WSProgressHandler"] = []

    def __init__(self, websocket: WebSocket, client_id: str):
        """
        Initialize the WebSocket handler.

        ### Arguments
        - websocket: The WebSocket instance.
        - client_id: The client's ID.
        """

        self.client_id = client_id
        self.websocket = websocket

    async def connect(self):
        """
        Called when a new client connects to the websocket.
        """

        connection = {"client_id": self.client_id, "websocket": self.websocket}
        logging.info("Connecting WebSocket: %s", connection)
        await self.websocket.accept()
        WSProgressHandler.instances.append(self)

    @classmethod
    def get(cls, client_id: str):
        """
        Get a WSProgressHandler instance by client_id.

        ### Arguments
        - client_id: The client's ID.
        """

        try:
            instance = next(
                inst for inst in cls.instances if inst.client_id == client_id
            )
            return instance
        except StopIteration:
            logging.warning(
                "Error while accessing websocket instance. Websocket not created"
            )
            return None

    async def send_update(self, message: str):
        """
        Send an update to the client.

        ### Arguments
        - message: The message to send.
        """

        logging.debug("Sending %s: %s", self.client_id, message)
        await self.websocket.send_text(message)

    def update(self, progress_handler_instance: SongTracker, message: str):
        """Callback function from ProgressHandler's SongTracker, called on every update

        ### Arguments
        - progress_handler_instance: The ProgressHandler instance.
        - message: The message to send.
        """
        update_message = {
            "song": progress_handler_instance.song.json,
            "progress": progress_handler_instance.progress,
            "message": message,
        }
        asyncio.run(self.send_update(json.dumps(update_message)))


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


@app.server.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Websocket endpoint.

    ### Arguments
    - websocket: The WebSocket instance.
    - client_id: The client's ID.
    """

    await WSProgressHandler(websocket, client_id).connect()

    try:
        while True:
            data = await websocket.receive_text()
            logging.debug("Client %s said: %s", client_id, data)
    except WebSocketDisconnect:
        logging.info("Disconnecting WebSocket: %s", client_id)


@app.server.get("/api/song/search")
def song_from_search(query: str) -> Song:
    """
    Search for a song on spotify using search query.

    ### Arguments
    - query: The search query.

    ### Returns
    - returns the first result as a Song object.
    """

    return Song.from_search_term(query)


@app.server.get("/api/song/url")
def song_from_url(url: str) -> Song:
    """
    Search for a song on spotify using url.

    ### Arguments
    - url: The url to search.

    ### Returns
    - returns the first result as a Song object.
    """

    return Song.from_url(url)


@app.server.post("/api/songs/query")
def query_search(query: List[str]) -> List[Song]:
    """
    Parse a list of search queries.

    ### Arguments
    - query: The query to parse.

    ### Returns
    - returns a list of Song objects.
    """

    return parse_query(query)


@app.server.get("/api/songs/search")
def search_search(query: str) -> List[Song]:
    """
    Parse search term and return list of Song objects.

    ### Arguments
    - query: The query to parse.

    ### Returns
    - returns a list of Song objects.
    """

    # return parse_query([query], app.downloader.threads)
    return get_search_results(query)


@app.server.post("/api/downloader/change_output")
def change_output(output: str) -> bool:
    """
    Change output folder

    ### Arguments
    - output: The output folder.

    ### Returns
    - returns True if the output folder was changed.
    """

    app.downloader.output = output

    return True


@app.server.post("/api/downloader/download/search")
async def download_search(
    query: str, return_file: bool = False
) -> Union[Tuple[Song, Optional[Path]], FileResponse]:
    """
    Search for song and download the first result.

    ### Arguments
    - query: The query to search.
    - return_file: If True, return the file instead of the song.

    ### Returns
    - returns a Tuple of Song and Path if return_file is True.
    - returns a FileResponse if return_file is False.
    """

    song, path = await app.downloader.pool_download(Song.from_search_term(query))

    if return_file is True:
        if path is None:
            raise ValueError("No file found")

        return FileResponse(path)

    return song, path


@app.server.post("/api/download/objects")
async def download_objects(
    song: SongModel, return_file: bool = False
) -> Union[Tuple[Song, Optional[Path]], FileResponse]:
    """
    Download songs using Song objects.

    ### Arguments
    - song: The Song object.
    - return_file: If True, return the file instead of the song.

    ### Returns
    - returns a Tuple of Song and Path if return_file is True.
    - returns a FileResponse if return_file is False.
    """

    song_obj, path = await app.downloader.pool_download(Song(**song.dict()))

    if return_file is True:
        if path is None:
            raise ValueError("No file found")

        return FileResponse(path)

    return song_obj, path


@app.server.post("/api/download/url")
async def download_url(url: str, client_id: str) -> Optional[str]:
    """
    Download songs using Song url.

    ### Arguments
    - url: The url to download.
    - client_id: The client's ID.

    ### Returns
    - returns the file path if the song was downloaded.
    """

    app.downloader.output = str(
        (get_spotdl_path() / f"web/sessions/{client_id}").absolute()
    )

    # Initiate realtime updates if websocket from client is connected
    ws_instance = WSProgressHandler.get(client_id)
    if ws_instance is not None:
        app.downloader.progress_handler = ProgressHandler(
            NAME_TO_LEVEL[app.settings["log_level"]],
            simple_tui=True,
            update_callback=ws_instance.update,
        )

    try:
        # Fetch song metadata
        song = Song.from_url(url)

        # Download Song
        _, path = await app.downloader.pool_download(song)

        if path is None:
            exc = DownloaderError(f"Failure downloading {song.name}")
            logging.warning("Error downloading! %s", exc)
            raise HTTPException(status_code=500, detail=f"Error downloading: {exc}")

        # Strip Filename
        filename = os.path.basename(path)

        return filename

    except Exception as exception:
        logging.warning("Error downloading! %s", exception)
        raise HTTPException(
            status_code=500, detail=f"Error downloading: {exception}"
        ) from exception


@app.server.get("/api/download/file")
async def download_file(file: str, client_id: str) -> FileResponse:
    """
    Download file using path.

    ### Arguments
    - file: The file path.
    - client_id: The client's ID.

    ### Returns
    - returns the file response, filename specified to return as attachment.
    """

    return FileResponse(
        str((get_spotdl_path() / f"web/sessions/{client_id}/{file}").absolute()),
        filename=file,
    )


@app.server.post("/api/download/multiple_search")
def download_multiple_search(query: List[str]) -> List[Tuple[Song, Optional[Path]]]:
    """
    Search for song and download the first result.

    ### Arguments
    - query: The query to search.

    ### Returns
    - returns a list of Tuple of Song and Path if the song was downloaded.
    """

    return app.downloader.download_multiple_songs(parse_query(query))


@app.server.post("/api/download/multiple_objects")
def download_multiple_objects(
    songs: List[SongModel],
) -> List[Tuple[Song, Optional[Path]]]:
    """
    Download songs using Song objects.

    ### Arguments
    - songs: The list of Song objects.

    ### Returns
    - returns a list of Tuple of Song and Path if the song was downloaded.
    """

    return app.downloader.download_multiple_songs(
        [Song.from_dict(song.dict()) for song in songs]
    )


@app.server.get("/api/settings")
def get_settings() -> SettingsModel:
    """
    Return the settings object.

    ### Returns
    - returns the settings object.
    """

    return SettingsModel(**app.settings)


@app.server.post("/api/settings/update")
def change_settings(settings: SettingsModel) -> bool:
    """
    Change downloader settings by re-initializing the downloader.

    ### Arguments
    - settings: The settings to change.

    ### Returns
    - returns True if the settings were changed.
    """

    settings_dict = settings.dict()

    # Create shallow copy of settings
    settings_cpy = app.settings.copy()

    # Update settings with new settings that are not None
    settings_cpy.update({k: v for k, v in settings_dict.items() if v is not None})

    logging.debug("Applying settings: %s", {settings_cpy})

    # Re-initialize downloader
    app.downloader = Downloader(
        audio_providers=settings_cpy["audio_providers"],
        lyrics_providers=settings_cpy["lyrics_providers"],
        ffmpeg=settings_cpy["ffmpeg"],
        bitrate=settings_cpy["bitrate"],
        ffmpeg_args=settings_cpy["ffmpeg_args"],
        output_format=settings_cpy["format"],
        save_file=settings_cpy["save_file"],
        threads=settings_cpy["threads"],
        output=settings_cpy["output"],
        overwrite=settings_cpy["overwrite"],
        log_level="CRITICAL",
        simple_tui=True,
        loop=app.loop,
    )

    return True


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


def web(settings: Dict[str, Any]):
    """
    Run the web server.

    ### Arguments
    - settings: Settings dictionary, based on the `SettingsModel` class.
    """

    fix_mime_types()

    web_app_dir = str(get_spotdl_path().absolute())

    print("Updating web app")

    # Get web client from CDN (github for now)
    download_github_dir(
        "https://github.com/spotdl/web-ui/tree/master/dist", output_dir=web_app_dir
    )

    # Serve web client SPA
    app.server.mount(
        "/", SPAStaticFiles(directory=web_app_dir + "/dist", html=True), name="static"
    )

    loop = asyncio.new_event_loop()

    app.loop = loop
    app.settings = settings
    app.downloader = Downloader(
        audio_providers=settings["audio_providers"],
        lyrics_providers=settings["lyrics_providers"],
        ffmpeg=settings["ffmpeg"],
        bitrate=settings["bitrate"],
        ffmpeg_args=settings["ffmpeg_args"],
        output_format=settings["format"],
        save_file=settings["save_file"],
        threads=settings["threads"],
        output=settings["output"],
        overwrite=settings["overwrite"],
        log_level=settings["log_level"],
        simple_tui=True,
        loop=loop,
    )

    config = Config(app=app.server, port=8800, workers=1, loop=loop)  # type: ignore

    server = Server(config)

    webbrowser.open("http://localhost:8800")

    loop.run_until_complete(server.serve())

    app.downloader.progress_handler.close()
