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
from spotdl.utils.search import get_search_results, get_simple_songs
from spotdl.utils.web import Client, app_state, validate_search_term
from spotdl.web.utils import Signals, handle_signals

__all__ = ["router"]

router = APIRouter()

# Resolve the templates directory relative to this package so the web UI works
# regardless of the current working directory (e.g. inside Docker, WORKDIR=/music).
templates = Jinja2Templates(directory=str(Path(__file__).parent / "components"))

# Strong references to background download tasks.
# asyncio only keeps a *weak* reference to tasks created with create_task(),
# so without this the task can be garbage-collected the moment it suspends on
# its first `await` (e.g. await asyncio.to_thread(Playlist.from_url, ...)),
# causing the download to silently vanish.
_background_tasks: set = set()


def _spawn_background_task(coro) -> None:
    """
    Schedule a coroutine as a background task and retain a strong reference to
    it until it completes, so it is not garbage-collected mid-execution.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


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

    # If the client ID is stale (server restarted), create a new one and inform the browser.
    if signals.client_id and Client.get_instance(signals.client_id) is None:
        app_state.logger.warning(
            f"Client {signals.client_id} not found in search, creating new client..."
        )
        signals.client_id = uuid.uuid4().hex
        client = Client(signals.client_id)
        await client.connect()
        yield SSE.patch_signals({"client_id": signals.client_id})

    app_state.logger.info(f"[{signals.client_id}] Search term: {signals.search_term}")
    is_valid_url = validate_search_term(signals.search_term)

    if is_valid_url:
        app_state.logger.info(
            f"[{signals.client_id}] Valid URL detected, redirecting to downloads..."
        )
        signals.song_url = signals.search_term
        # Start the download as a background task BEFORE redirecting.
        # If we redirect first, the browser closes this SSE connection and the
        # generator gets cancelled before gen_download can run.
        _spawn_background_task(_run_download_task(signals))
        yield SSE.redirect("/downloads")
        return

    songs = get_search_results(signals.search_term)
    yield SSE.patch_elements(
        templates.get_template("search-list.html.j2").render(
            songs=songs,
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
                client_song_downloads=client_song_downloads.values()
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
    async for update in gen_download(signals):
        yield update


# HELPERS


async def _run_download_task(signals: Signals):
    """
    Background task wrapper for gen_download.
    Consumes the generator without yielding to any SSE stream,
    so it survives the closure of the search SSE connection.
    Deduplicates by URL so datastar retries don't trigger multiple downloads.
    """
    app_state.logger.info(
        f"[{signals.client_id}] Background download task started for: {signals.song_url}"
    )
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"[{signals.client_id}] Client not found in background task, aborting."
        )
        return
    url = signals.song_url
    if url in client.active_download_urls:
        app_state.logger.info(
            f"[{signals.client_id}] Download already in progress for {url}, skipping duplicate."
        )
        return
    client.active_download_urls.add(url)
    try:
        async for _ in gen_download(signals):
            pass
    except BaseException as exc:
        app_state.logger.error(
            f"[{signals.client_id}] Background download task failed ({type(exc).__name__}): {exc}"
        )
    finally:
        client.active_download_urls.discard(url)
        app_state.logger.info(
            f"[{signals.client_id}] Background download task finished for: {url}"
        )


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
        client.downloader.settings["output"] = client.downloader_settings["output"]
    else:
        client.downloader.settings["output"] = str(
            (get_spotdl_path() / f"web/sessions/{client.client_id}").absolute()
        )

    try:
        url = signals.song_url
        app_state.logger.info(f"[{signals.client_id}] Resolving URL: {url}")

        # Resolve the URL (track / playlist / album / artist) into a flat list of
        # Song objects using the same canonical resolver the CLI uses.
        # get_simple_songs():
        #   * already calls *.from_url(url, fetch_songs=False), so it does NOT
        #     make one slow Spotify call per song (doing so made playlists appear
        #     to hang), and
        #   * populates each song's list_name/list_url/list_position/list_length,
        #     which the output template "{list-name}/..." relies on. Without it the
        #     template collapses to "/..." (an absolute path to the filesystem
        #     root) and ffmpeg fails with "Permission denied".
        # It internally calls asyncio.run() via spotipyfree, so it must run in a
        # worker thread to avoid clashing with the server's running event loop.
        app_state.logger.info(f"[{signals.client_id}] Fetching metadata...")
        songs = await asyncio.to_thread(get_simple_songs, [url])

        app_state.logger.info(f"[{signals.client_id}] Resolved {len(songs)} song(s), starting download from: {url}")

        # Download all songs concurrently. pool_download() acquires the
        # downloader's semaphore (sized to the "threads" setting, e.g. 4), so
        # gathering every task at once still only runs N downloads in parallel
        # instead of one-at-a-time.
        client.downloader.progress_handler.set_song_count(len(songs))
        results = await asyncio.gather(
            *(client.downloader.pool_download(song) for song in songs),
            return_exceptions=True,
        )
        for song, result in zip(songs, results):
            if isinstance(result, BaseException):
                app_state.logger.error(
                    f"[{signals.client_id}] Error downloading {song.name}: {result}"
                )
                continue
            _, path = result
            if path is None:
                app_state.logger.error(f"Failure downloading {song.name}")

        yield SSE.patch_elements(f"""
            <button id="download-{signals.song_url}" class="btn btn-primary btn-square">
                    <iconify-icon icon="clarity:check-line" style="font-size: 24px"></iconify-icon>
                </button>
        """)

    except Exception as exception:
        app_state.logger.error(f"Error downloading! {exception}")


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
