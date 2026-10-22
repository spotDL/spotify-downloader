"""
Module for handling API requests.
"""

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from spotdl._version import __version__
from spotdl.download.downloader import Downloader
from spotdl.types.album import Album
from spotdl.types.artist import Artist
from spotdl.types.options import DownloaderOptionalOptions, DownloaderOptions
from spotdl.types.playlist import Playlist
from spotdl.types.song import Song
from spotdl.utils.arguments import create_parser
from spotdl.utils.config import get_spotdl_path
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.github import RateLimitError, get_latest_version, get_status
from spotdl.utils.search import get_search_results
from spotdl.utils.web import (
    ApplicationState,
    Client,
    app_state,
    get_client,
    get_current_state,
)

__all__ = [
    "query_search",
    "download_url",
    "download_file",
    "get_settings",
    "update_settings",
]

router = APIRouter()

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

# Client ids are used in session directory names, so keep them path-safe.
# The web UI generates UUIDs.
CLIENT_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


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


# @router.websocket("/api/ws")
# async def websocket_endpoint(websocket: WebSocket, client_id: str):
#     """
#     Websocket endpoint.

#     ### Arguments
#     - websocket: The WebSocket instance.
#     """

#     await Client(websocket, client_id).connect()

#     try:
#         while True:
#             await websocket.receive_json()
#     except WebSocketDisconnect:
#         app_state.clients.pop(client_id, None)

#         if (
#             len(app_state.clients) == 0
#             and app_state.web_settings["keep_alive"] is False
#         ):
#             app_state.logger.debug(
#                 "No active connections, waiting 1s before shutting down"
#             )

#             await asyncio.sleep(1)

#             # Wait 1 second before shutting down
#             # This is to prevent the server from shutting down when a client
#             # disconnects and reconnects quickly (e.g. when refreshing the page)
#             if len(app_state.clients) == 0:
#                 # Perform a clean exit
#                 app_state.logger.info("Shutting down server, no active connections")
#                 app_state.server.force_exit = True
#                 app_state.server.should_exit = True
#                 await app_state.server.shutdown()


@router.get("/api/connect")
async def connect_endpoint(client_id: str):
    """
    Websocket endpoint.

    ### Arguments
    - websocket: The WebSocket instance.
    """

    if not CLIENT_ID_REGEX.match(client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id.")

    await Client(client_id).connect()


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

    if state.web_settings.get("web_use_output_dir", False):
        # Use the static part of the output template, if it ends partway
        # through a file name, use the directory that file would be in
        output_prefix = client.downloader_settings["output"].split("{", 1)[0]
        expected_dir = Path(output_prefix)
        if not output_prefix.endswith(("/", os.sep)):
            expected_dir = expected_dir.parent
    else:
        expected_dir = get_spotdl_path() / f"web/sessions/{client.client_id}"

    # Resolve both paths so ".." segments and symlinks can't escape the directory
    file_path = Path(file).resolve()
    if (file_path.suffix[1:] not in FFMPEG_FORMATS) or (
        not file_path.is_relative_to(expected_dir.resolve())
    ):
        raise HTTPException(status_code=400, detail="Invalid download path.")

    return FileResponse(
        file_path,
        filename=file_path.name,
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

    actions = {
        action.dest: action
        for action in create_parser()._actions  # pylint: disable=protected-access
    }

    changes = {}
    for key, value in settings.items():
        # The web UI sends back every setting it received, so unchanged values
        # (including ones it isn't allowed to change) are expected and skipped
        if value is None or value == client.downloader_settings.get(key):
            continue

        if key not in WEB_EDITABLE_SETTINGS:
            state.logger.warning(
                f"Ignoring setting that can't be changed from the web UI: {key}"
            )
            continue

        error = validate_setting(key, value, actions[key])
        if error is not None:
            raise HTTPException(status_code=400, detail=error)

        changes[key] = value

    # Create shallow copy of settings
    settings_cpy = client.downloader_settings.copy()

    # Update settings with the allowed changes
    settings_cpy.update(changes)  # type: ignore

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

    options = {}
    for action in parser._actions:  # pylint: disable=protected-access
        if action.dest not in WEB_EDITABLE_SETTINGS:
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
