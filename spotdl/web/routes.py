"""
Module which contains the web client routes and functions.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Any, Optional, cast

# from datastar_py.sse import DatastarEvent
from datastar_py.fastapi import ReadSignals
from datastar_py.fastapi import (
    ServerSentEventGenerator as SSE,  # DatastarResponse,; read_signals,
)
from datastar_py.fastapi import datastar_response
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from spotdl._version import __version__
from spotdl.download.downloader import AUDIO_PROVIDERS, LYRICS_PROVIDERS
from spotdl.utils.config import get_spotdl_path
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.search import parse_query
from spotdl.utils.web import (
    Client,
    app_state,
    normalize_spotify_url,
    validate_search_term,
)
from spotdl.utils.web_folders import folder_destination, music_folders
from spotdl.utils.web_search import get_search_results
from spotdl.web.utils import Signals, handle_signals

__all__ = ["router"]

router = APIRouter()

templates = Jinja2Templates(directory=Path(__file__).parent / "components")


# PATHS


@router.get("/")
async def home(request: Request):
    """
    Handle the home page request.
    """
    return templates.TemplateResponse(
        name="home.html.j2",
        context={"request": request, "__version__": __version__},
    )


@router.get("/search")
async def search(q: Optional[str], request: Request):
    """
    Handle the search input.
    """
    return templates.TemplateResponse(
        name="search.html.j2",
        context={"request": request, "__version__": __version__, "search_term": q},
    )


@router.get("/downloads")
async def downloads(request: Request):
    """
    Handle the downloads page request.
    """
    return templates.TemplateResponse(
        name="downloads.html.j2",
        context={
            "request": request,
            "__version__": __version__,
        },
    )


# ACTIONS


@router.get("/client/load")
@datastar_response
async def handle_get_client_load(datastar_signals: ReadSignals):
    """
    Handle the loading of the client.
    """
    app_state.logger.info("Loading client...")
    signals = handle_signals(datastar_signals)
    if not signals.client_id:
        # Generate a new client ID if not provided
        app_state.logger.warning("No client ID provided, generating a new one.")
        signals.client_id = uuid.uuid4().hex
        client = Client(signals.client_id)
    else:
        found_client = Client.get_instance(signals.client_id)
        if found_client is None:
            # Create a new client if not found
            app_state.logger.warning(
                f"Client {signals.client_id} not found, creating new client..."
            )
            signals.client_id = uuid.uuid4().hex
            client = Client(signals.client_id)
        else:
            client = found_client
    await client.connect()

    # First send the client ID and then the home template.
    yield SSE.patch_elements("""<div id="status"></div>""")
    # Send the client ID to the client
    yield SSE.patch_signals(
        {
            "client_id": client.client_id,
        }
    )
    try:
        while True:
            yield SSE.patch_elements(f"""<div id="overall-completed-tasks">
                {len(client.downloader.progress_handler.progress_tracker.songs)}
                </div>""")
            await asyncio.sleep(1)
    finally:
        app_state.logger.info(f"[{signals.client_id}] Unloading client...")
        await client.disconnect()


@router.get("/client/search")
@datastar_response
async def handle_get_client_search(datastar_signals: ReadSignals):
    """
    Handle the search input.
    """
    app_state.logger.info("Loading search...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"[{signals.client_id}] Search term: {signals.search_term}")
    signals.search_term = normalize_spotify_url(signals.search_term)
    is_valid_url = validate_search_term(signals.search_term)

    if is_valid_url:
        # redirect client to downloads page
        app_state.logger.info(
            f"[{signals.client_id}] Valid URL detected, redirecting to downloads..."
        )
        signals.song_url = signals.search_term
        if start_background_download(signals):
            yield SSE.redirect("/downloads")
        else:
            yield SSE.patch_elements(
                templates.get_template("status-disconnected.html.j2").render()
            )
        return

    try:
        songs = await asyncio.wait_for(
            asyncio.to_thread(get_search_results, signals.search_term), timeout=45
        )
        app_state.logger.info("Search returned %s songs", len(songs))
        yield SSE.patch_elements(
            templates.get_template("search-list.html.j2").render(songs=songs)
        )
    except asyncio.TimeoutError:
        app_state.logger.warning("Search timed out: %s", signals.search_term)
        yield SSE.patch_elements(
            templates.get_template("search-error.html.j2").render(
                message="Spotify search did not respond within 45 seconds. Try again or paste a Spotify URL."
            )
        )
    except Exception:
        app_state.logger.exception("Web search failed: %s", signals.search_term)
        yield SSE.patch_elements(
            templates.get_template("search-error.html.j2").render(
                message="Unable to retrieve search results. Check the server log or try a Spotify URL."
            )
        )


@router.get("/client/downloads")
@datastar_response
async def handle_get_client_downloads(datastar_signals: ReadSignals):
    """
    Handle the retrieval of client downloads.
    """
    app_state.logger.info("Loading downloads...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"[{signals.client_id}] Downloads requested.")
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"[{signals.client_id}] Client not found, cannot load downloads."
        )
        yield SSE.patch_elements(
            templates.get_template("status-disconnected.html.j2").render()
        )
        return
    while True:
        client_song_downloads = (
            client.downloader.progress_handler.progress_tracker.songs
        )
        yield SSE.patch_elements(
            templates.get_template("download-list.html.j2").render(
                client_song_downloads=client_song_downloads.values(),
                download_status=getattr(client, "download_status", {}),
            )
        )
        await asyncio.sleep(1)


@router.get("/client/settings")
@datastar_response
async def handle_get_client_settings(datastar_signals: ReadSignals):
    """
    Handle the retrieval of client settings.
    """
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, cannot update settings."
        )
        yield SSE.patch_elements(
            templates.get_template("status-disconnected.html.j2").render()
        )
        return
    app_state.logger.info(f"[{signals.client_id}] Sending client settings...")
    yield SSE.patch_signals(
        {
            "downloader_settings": cast(Any, client.downloader_settings),
        }
    )


@router.post("/client/settings")
@datastar_response
async def handle_post_client_settings(datastar_signals: ReadSignals):
    """
    Handle the update of client settings.
    """
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is not None:
        app_state.logger.info(f"[{signals.client_id}] Updating settings...")
        if signals.downloader_settings is not None:
            client.downloader_settings = signals.downloader_settings
        yield SSE.patch_elements("""
                <div id="settings-status">
                    <div id="settings-is-saved" class="alert alert-success shadow-lg">
                        <div>
                            <svg 
                            xmlns="http://www.w3.org/2000/svg" 
                            class="stroke-current flex-shrink-0 h-6 w-6" 
                            fill="none"
                            viewBox="0 0 24 24">
                                <path 
                                stroke-linecap="round" 
                                stroke-linejoin="round" 
                                stroke-width="2"
                                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>Changes saved</span>
                        </div>
                    </div>
                </div>
            """)
        yield SSE.patch_signals(
            {
                "downloader_settings": cast(Any, client.downloader_settings),
            }
        )
    else:
        app_state.logger.warning(
            f"[{signals.client_id}] Client not found, cannot update settings."
        )
        yield SSE.patch_elements(
            templates.get_template("status-disconnected.html.j2").render()
        )
        yield SSE.patch_elements("""
                <div id="settings-status">
                    <div id="settings-is-not-saved" class="alert alert-error shadow-lg">
                        <div>
                            <svg 
                            xmlns="http://www.w3.org/2000/svg" 
                            class="stroke-current 
                            flex-shrink-0 h-6 w-6" 
                            fill="none"
                            viewBox="0 0 24 24">
                                <path 
                                stroke-linecap="round" 
                                stroke-linejoin="round" 
                                stroke-width="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" 
                            />
                            </svg>
                            <span>Error! Unable to save settings</span>
                        </div>
                    </div>
                </div>
            """)
    #  sleep for 3 seconds then clear the status message
    await asyncio.sleep(3)
    yield SSE.patch_elements("""
            <div id="settings-status">
            </div>
        """)


@router.post("/client/download/")
@datastar_response
async def handle_post_client_download(datastar_signals: ReadSignals):
    """
    Handle the download request from the client.
    """
    signals = handle_signals(datastar_signals)
    if start_background_download(signals):
        yield SSE.redirect("/downloads")
    else:
        yield SSE.patch_elements(
            templates.get_template("status-disconnected.html.j2").render()
        )


# HELPERS


async def consume_download(signals: Signals) -> None:
    """Process the download without tying it to an SSE connection."""
    client = Client.get_instance(signals.client_id)
    if client is None:
        return
    async with client.download_lock:
        async for _ in gen_download(signals):
            pass


def start_background_download(signals: Signals) -> bool:
    """Start a download before returning a redirect to the browser."""
    client = Client.get_instance(signals.client_id)
    if client is None:
        return False
    signals.download_output = (
        getattr(client, "music_output", None) or client.downloader_settings["output"]
    )
    client.start_download(consume_download(signals))
    return True


async def gen_download(signals: Signals):
    """
    Generate the download process for the client.
    """
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, cannot load downloads."
        )
        yield SSE.patch_elements(
            templates.get_template("status-disconnected.html.j2").render()
        )
        return
    app_state.logger.info(
        f"[{signals.client_id}] Download requested: {signals.song_url}"
    )
    yield SSE.patch_elements(f"""
            <button id="download-{signals.song_url}" class="btn btn-primary btn-square loading">
                </button>
        """)

    if app_state.web_settings.get("web_use_output_dir", False):
        client.downloader.settings["output"] = (
            signals.download_output
            or getattr(client, "music_output", None)
            or client.downloader_settings["output"]
        )
    else:
        client.downloader.settings["output"] = str(
            (get_spotdl_path() / f"web/sessions/{client.client_id}").absolute()
        )

    client.download_status = {
        "phase": "Reading song or playlist",
        "total": 0,
        "processed": 0,
        "failures": 0,
        "song": "",
        "output": client.downloader.settings["output"],
    }
    try:
        songs = await asyncio.to_thread(
            parse_query,
            [normalize_spotify_url(signals.song_url)],
            threads=1,
            use_ytm_data=client.downloader_settings.get("ytm_data", False),
            playlist_numbering=client.downloader_settings.get(
                "playlist_numbering", False
            ),
            playlist_retain_track_cover=client.downloader_settings.get(
                "playlist_retain_track_cover", False
            ),
        )
        if not songs:
            raise ValueError("No songs found for this URL.")

        progress = client.downloader.progress_handler
        progress.set_song_count(progress.song_count + len(songs))
        failed = False
        client.download_status.update(phase="Downloading", total=len(songs))
        for song in songs:
            client.download_status["song"] = song.name
            song_failed = False
            try:
                _, path = await client.downloader.pool_download(song)
                if path is None:
                    failed = True
                    song_failed = True
                    app_state.logger.error("Failure downloading %s", song.name)
            except Exception:
                failed = True
                song_failed = True
                app_state.logger.exception("Error downloading %s", song.name)

            client.download_status["processed"] += 1
            client.download_status["failures"] += int(song_failed)
        client.download_status["phase"] = "Finished"
        icon = "clarity:error-line" if failed else "clarity:check-line"
        yield SSE.patch_elements(
            f'<button id="download-{signals.song_url}" '
            f'class="btn btn-primary btn-square">'
            f'<iconify-icon icon="{icon}" style="font-size: 24px">'
            "</iconify-icon></button>"
        )
    except Exception:
        client.download_status["phase"] = (
            "Failed to read or process this request; check server logs"
        )
        app_state.logger.exception("Error processing download request")


# COMPONENTS


@router.get("/client/component/settings-content")
@datastar_response
async def handle_get_client_component_settings(datastar_signals: ReadSignals):
    """
    Handle the request for the client settings component.
    """
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, cannot update settings."
        )
        yield SSE.patch_elements(
            templates.get_template("status-disconnected.html.j2").render()
        )
        return
    app_state.logger.info(f"[{signals.client_id}] Loading settings view...")
    # clear state
    yield SSE.patch_elements("""<div id="component-settings-content"></div>""")
    # render the settings content
    yield SSE.patch_elements(
        templates.get_template("settings-content.html.j2").render(
            downloader_settings=client.downloader_settings,
            AUDIO_PROVIDERS=AUDIO_PROVIDERS,
            LYRICS_PROVIDERS=LYRICS_PROVIDERS,
            FORMATS=FFMPEG_FORMATS.keys(),
            selected_music_folder=(
                Path(cast(str, client.music_output)).parent.name
                if getattr(client, "music_output", None)
                and client.music_output != app_state.downloader_settings["output"]
                else ""
            ),
            folder_picker=app_state.web_settings.get("web_use_output_dir", False),
            music_folders=(
                music_folders(app_state.downloader_settings["output"])
                if app_state.web_settings.get("web_use_output_dir", False)
                else []
            ),
        )
    )
    # spotify_client = SpotifyClient()
    # print(f"{spotify_client = }")
    yield SSE.patch_signals(
        {
            "downloader_settings": cast(Any, client.downloader_settings),
            # "spotify_settings": {
            #     "client_id": spotify_client.credential_manager.client_id
            # },
        }
    )


@router.get("/client/component/search-input-rotating-placeholder")
@datastar_response
async def handle_client_component_search_input_rotating_placeholder():
    """
    Handle the search input rotating placeholder component.
    """
    app_state.logger.info("Loading rotating-placeholder...")
    placeholder_items = [
        "All Eyes On Me - Bo Burnham",
        "https://open.spotify.com/track/4vfN00PlILRXy5dcXHQE9M?si=e4d9e7c044dd4a8f",
        "Lil Wayne",
        "Drive - Miley Cyrus",
        "Sofia - TMG",
        "Lightning Crashes - Live",
    ]
    index = 0
    while True:
        t = templates.get_template("search-input-rotating-placeholder.html.j2").render(
            placeholder_item=placeholder_items[index]
        )
        yield SSE.patch_elements(t)
        await asyncio.sleep(5)
        index += 1
        if index >= len(placeholder_items):
            index = 0


@router.post("/client/music-folder")
@datastar_response
async def handle_music_folder(datastar_signals: ReadSignals):
    """Apply a confined destination to future requests in this session."""
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is None or not app_state.web_settings.get("web_use_output_dir", False):
        return
    try:
        name = signals.new_music_folder.strip() or signals.music_folder
        client.music_output = folder_destination(
            app_state.downloader_settings["output"],
            name,
            create=bool(signals.new_music_folder.strip()),
        )
        yield SSE.patch_elements(
            templates.get_template("folder-status.html.j2").render(
                output=client.music_output
            )
        )
    except (ValueError, OSError) as error:
        yield SSE.patch_elements(
            templates.get_template("folder-status.html.j2").render(error=str(error))
        )
