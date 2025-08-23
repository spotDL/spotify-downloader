import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datastar_py.fastapi import (
    # DatastarResponse,
    datastar_response,
    ReadSignals,
    # read_signals,
    ServerSentEventGenerator as SSE,
)
# from datastar_py.sse import DatastarEvent
# from spotdl.utils.web import validate_search_term

from spotdl._version import __version__

# import spotdl.web.components.components as components
from spotdl.web.utils import handle_signals
from spotdl.utils.web import Client, app_state
from spotdl.download.downloader import AUDIO_PROVIDERS, LYRICS_PROVIDERS
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.search import get_search_results

__all__ = ["router"]

router = APIRouter()

templates = Jinja2Templates(directory="spotdl/web/components")


# PATHS


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="home.html.j2",
        context={"request": request, "__version__": __version__},
    )


@router.get("/search")
async def search(q: Optional[str], request: Request):
    return templates.TemplateResponse(
        name="search.html.j2",
        context={"request": request, "__version__": __version__, "search_term": q},
    )


@router.get("/downloads")
async def downloads(request: Request):
    return templates.TemplateResponse(
        name="downloads.html.j2",
        context={"request": request, "__version__": __version__},
    )


# ACTIONS


@router.get("/client/load")
@datastar_response
async def handle_get_client_load(datastar_signals: ReadSignals):
    app_state.logger.info("Loading client...")
    signals = handle_signals(datastar_signals)
    if not signals.client_id:
        # Generate a new client ID if not provided
        app_state.logger.warning("No client ID provided, generating a new one.")
        signals.client_id = uuid.uuid4().hex
        client = Client(signals.client_id)
    else:
        client = Client.get_instance(signals.client_id)
        if client is None:
            # Create a new client if not found
            app_state.logger.warning(
                f"Client {signals.client_id} not found, creating new client..."
            )
            signals.client_id = uuid.uuid4().hex
            client = Client(signals.client_id)
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
            # while client.update_stack:
            # update = client.update_stack.pop(0)
            # yield SSE.patch_signals(update)
            # print(client.downloader.progress_handler.overall_completed_tasks)
            yield SSE.patch_elements(
                f"""<div id="overall-completed-tasks">{client.downloader.progress_handler.overall_completed_tasks}</div>"""
            )
            await asyncio.sleep(1)
    finally:
        app_state.logger.info(f"[{signals.client_id}] Unloading client...")
        await client.disconnect()


@router.get("/client/search")
@datastar_response
async def handle_get_client_search(datastar_signals: ReadSignals):
    app_state.logger.info("Loading search...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"[{signals.client_id}] Search term: {signals.search_term}")
    # is_valid = validate_search_term(signals.search_term)
    songs = get_search_results(signals.search_term)
    yield SSE.patch_elements(
        templates.get_template("search-list.html.j2").render(
            songs=songs,
        )
    )


@router.get("/client/settings")
@datastar_response
async def handle_get_client_settings(datastar_signals: ReadSignals):
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, cannot update settings."
        )
        yield SSE.patch_elements(templates.get_template("status-disconnected.html.j2"))
        return
    app_state.logger.info(f"[{signals.client_id}] Sending client settings...")
    yield SSE.patch_signals(
        {
            "downloader_settings": client.downloader_settings,
        }
    )


@router.post("/client/settings")
@datastar_response
async def handle_post_client_settings(datastar_signals: ReadSignals):
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is not None:
        app_state.logger.info(f"[{signals.client_id}] Updating settings...")
        client.downloader_settings = signals.downloader_settings
        yield SSE.patch_elements(
            """
                <div id="settings-status">
                    <div id="settings-is-saved" class="alert alert-success shadow-lg">
                        <div>
                            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none"
                                viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>Changes saved</span>
                        </div>
                    </div>
                </div>
            """
        )
        yield SSE.patch_signals(
            {
                "downloader_settings": client.downloader_settings,
            }
        )
    else:
        app_state.logger.warning(
            f"[{signals.client_id}] Client not found, cannot update settings."
        )
        yield SSE.patch_elements(templates.get_template("status-disconnected.html.j2"))
        yield SSE.patch_elements(
            """
                <div id="settings-status">
                    <div id="settings-is-not-saved" class="alert alert-error shadow-lg">
                        <div>
                            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none"
                                viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>Error! Unable to save settings</span>
                        </div>
                    </div>
                </div>
            """
        )
    #  sleep for 3 seconds then clear the status message
    await asyncio.sleep(3)
    yield SSE.patch_elements(
        """
            <div id="settings-status">
            </div>
        """
    )


# COMPONENTS


@router.get("/client/component/settings-content")
@datastar_response
async def handle_get_client_component_settings(datastar_signals: ReadSignals):
    signals = handle_signals(datastar_signals)
    client = Client.get_instance(signals.client_id)
    if client is None:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, cannot update settings."
        )
        yield SSE.patch_elements(templates.get_template("status-disconnected.html.j2"))
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
    yield SSE.patch_signals(
        {
            "downloader_settings": client.downloader_settings,
        }
    )


@router.get("/client/component/search-input-rotating-placeholder")
@datastar_response
async def handle_client_component_search_input_rotating_placeholder(
    signals: ReadSignals,
):
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
