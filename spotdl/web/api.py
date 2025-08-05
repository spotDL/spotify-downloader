import argparse
import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse

from spotdl._version import __version__
from spotdl.download.downloader import Downloader
from spotdl.download.progress_handler import ProgressHandler
from spotdl.types.album import Album
from spotdl.types.artist import Artist
from spotdl.types.options import (
    DownloaderOptionalOptions,
    DownloaderOptions,
)
from spotdl.types.playlist import Playlist
from spotdl.types.song import Song
from spotdl.utils.arguments import create_parser
from spotdl.utils.config import (
    get_spotdl_path,
)
from spotdl.utils.github import RateLimitError, get_latest_version, get_status
from spotdl.utils.search import get_search_results

from spotdl.utils.web import (
    Client,
    ApplicationState,
    get_current_state,
    get_client,
)

__all__ = [
    "websocket_endpoint",
    "song_from_url",
    "query_search",
    "download_url",
    "download_file",
    "get_settings",
    "update_settings",
]

router = APIRouter()
app_state: ApplicationState = ApplicationState()


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Websocket endpoint.

    ### Arguments
    - websocket: The WebSocket instance.
    """

    await Client(websocket, client_id).connect()

    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        app_state.clients.pop(client_id, None)

        if (
            len(app_state.clients) == 0
            and app_state.web_settings["keep_alive"] is False
        ):
            app_state.logger.debug(
                "No active connections, waiting 1s before shutting down"
            )

            await asyncio.sleep(1)

            # Wait 1 second before shutting down
            # This is to prevent the server from shutting down when a client
            # disconnects and reconnects quickly (e.g. when refreshing the page)
            if len(app_state.clients) == 0:
                # Perform a clean exit
                app_state.logger.info("Shutting down server, no active connections")
                app_state.server.force_exit = True
                app_state.server.should_exit = True
                await app_state.server.shutdown()


# Deprecated
@router.get("/api/song/url", response_model=None)
def song_from_url(url: str) -> Song:
    """
    Search for a song on spotify using url.

    ### Arguments
    - url: The url to search.

    ### Returns
    - returns the first result as a Song object.
    """

    return Song.from_url(url)


@router.get("/api/url", response_model=None)
def songs_from_url(url: str) -> List[Song]:
    """
    Search for a song, playlist, artist or album on spotify using url.

    ### Arguments
    - url: The url to search.

    ### Returns
    - returns a list with Song objects to be downloaded.
    """

    if "playlist" in url:
        playlist = Playlist.from_url(url)
        return list(map(Song.from_url, playlist.urls))
    if "album" in url:
        album = Album.from_url(url)
        return list(map(Song.from_url, album.urls))
    if "artist" in url:
        artist = Artist.from_url(url)
        return list(map(Song.from_url, artist.urls))

    return [Song.from_url(url)]


@router.get("/api/version", response_model=None)
def version() -> str:
    """
    Get the current version
    This method is created to ensure backward compatibility of the web app,
    as the web app is updated with the latest regardless of the backend version

    ### Returns
    -  returns the version of the app
    """

    return __version__


@router.on_event("shutdown")
async def shutdown_event():
    """
    Called when the server is shutting down.
    """

    if (
        not app_state.web_settings["keep_sessions"]
        and not app_state.web_settings["web_use_output_dir"]
    ):
        app_state.logger.info("Removing sessions directories")
        sessions_dir = Path(get_spotdl_path(), "web/sessions")
        if sessions_dir.exists():
            shutil.rmtree(sessions_dir)


@router.get("/api/songs/search", response_model=None)
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
    url: str,
    client: Client = Depends(get_client),
    state: ApplicationState = Depends(get_current_state),
) -> Optional[str]:
    """
    Download songs using Song url.

    ### Arguments
    - url: The url to download.

    ### Returns
    - returns the file path if the song was downloaded.
    """

    if state.web_settings.get("web_use_output_dir", False):
        client.downloader.settings["output"] = client.downloader_settings["output"]
    else:
        client.downloader.settings["output"] = str(
            (get_spotdl_path() / f"web/sessions/{client.client_id}").absolute()
        )

    client.downloader.progress_handler = ProgressHandler(
        simple_tui=True,
        update_callback=client.song_update,
    )

    try:
        # Fetch song metadata
        song = Song.from_url(url)

        # Download Song
        _, path = await client.downloader.pool_download(song)

        if path is None:
            state.logger.error(f"Failure downloading {song.name}")

            raise HTTPException(
                status_code=500, detail=f"Error downloading: {song.name}"
            )

        return str(path.absolute())

    except Exception as exception:
        state.logger.error(f"Error downloading! {exception}")

        raise HTTPException(
            status_code=500, detail=f"Error downloading: {exception}"
        ) from exception


@router.get("/api/download/file")
async def download_file(
    file: str,
    client: Client = Depends(get_client),
    state: ApplicationState = Depends(get_current_state),
):
    """
    Download file using path.

    ### Arguments
    - file: The file path.
    - client: The client's state.

    ### Returns
    - returns the file response, filename specified to return as attachment.
    """

    expected_path = str((get_spotdl_path() / "web/sessions").absolute())
    if state.web_settings.get("web_use_output_dir", False):
        expected_path = str(
            Path(client.downloader_settings["output"].split("{", 1)[0]).absolute()
        )

    if (not file.endswith(client.downloader_settings["format"])) or (
        not file.startswith(expected_path)
    ):
        raise HTTPException(status_code=400, detail="Invalid download path.")

    return FileResponse(
        file,
        filename=os.path.basename(file),
    )


@router.get("/api/settings")
def get_settings(
    client: Client = Depends(get_client),
) -> DownloaderOptions:
    """
    Get client settings.

    ### Arguments
    - client: The client's state.

    ### Returns
    - returns the settings.
    """

    return client.downloader_settings


@router.post("/api/settings/update")
def update_settings(
    settings: DownloaderOptionalOptions,
    client: Client = Depends(get_client),
    state: ApplicationState = Depends(get_current_state),
) -> DownloaderOptions:
    """
    Update client settings, and re-initialize downloader.

    ### Arguments
    - settings: The settings to change.
    - client: The client's state.
    - state: The application state.

    ### Returns
    - returns True if the settings were changed.
    """

    # Create shallow copy of settings
    settings_cpy = client.downloader_settings.copy()

    # Update settings with new settings that are not None
    settings_cpy.update({k: v for k, v in settings.items() if v is not None})  # type: ignore

    state.logger.info(f"Applying settings: {settings_cpy}")

    new_settings = DownloaderOptions(**settings_cpy)  # type: ignore

    # Re-initialize downloader
    client.downloader_settings = new_settings
    client.downloader = Downloader(
        new_settings,
        loop=state.loop,
    )

    return new_settings


@router.get("/api/check_update")
def check_update() -> bool:
    """
    Check for update.

    ### Returns
    - returns True if there is an update.
    """

    try:
        _, ahead, _ = get_status(__version__, "master")
        if ahead > 0:
            return True
    except RuntimeError:
        latest_version = get_latest_version()
        latest_tuple = tuple(latest_version.replace("v", "").split("."))
        current_tuple = tuple(__version__.split("."))
        if latest_tuple > current_tuple:
            return True
    except RateLimitError:
        return False

    return False


@router.get("/api/options_model")
def get_options() -> Dict[str, Any]:
    """
    Get options model (possible settings).

    ### Returns
    - returns the options.
    """

    parser = create_parser()

    # Forbidden actions
    forbidden_actions = [
        "help",
        "operation",
        "version",
        "config",
        "user_auth",
        "client_id",
        "client_secret",
        "auth_token",
        "cache_path",
        "no_cache",
        "cookie_file",
        "ffmpeg",
        "archive",
        "host",
        "port",
        "keep_alive",
        "enable_tls",
        "key_file",
        "cert_file",
        "ca_file",
        "allowed_origins",
        "web_use_output_dir",
        "keep_sessions",
        "log_level",
        "simple_tui",
        "headless",
        "download_ffmpeg",
        "generate_config",
        "check_for_updates",
        "profile",
        "version",
    ]

    options = {}
    for action in parser._actions:  # pylint: disable=protected-access
        if action.dest in forbidden_actions:
            continue

        default = app_state.downloader_settings.get(action.dest, None)
        choices = list(action.choices) if action.choices else None

        type_name = ""
        if action.type is not None:
            if hasattr(action.type, "__objclass__"):
                type_name: str = action.type.__objclass__.__name__  # type: ignore
            else:
                type_name: str = action.type.__name__  # type: ignore

        if isinstance(
            action,
            argparse._StoreConstAction,  # pylint: disable=protected-access
        ):
            type_name = "bool"

        if choices is not None and action.nargs == "*":
            type_name = "list"

        options[action.dest] = {
            "type": type_name,
            "choices": choices,
            "default": default,
            "help": action.help,
        }

    return options
