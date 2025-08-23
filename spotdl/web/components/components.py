import asyncio
from multiprocessing import context
from typing import Optional
from datastar_py.fastapi import (
    DatastarResponse,
    datastar_response,
    ReadSignals,
    read_signals,
    ServerSentEventGenerator as SSE,
)
from datastar_py.sse import DatastarEvent
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import jinja2

from spotdl.download.downloader import AUDIO_PROVIDERS, LYRICS_PROVIDERS
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.search import get_search_results
from spotdl.utils.web import app_state
from spotdl.web.utils import handle_signals


router = APIRouter()
# env = jinja2.Environment(loader=jinja2.FileSystemLoader("spotdl/web/components"))
templates = Jinja2Templates(directory="spotdl/web/components")


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(name="home.html.j2", context={"request": request})


@router.get("/search")
async def search(q: Optional[str], request: Request):
    return templates.TemplateResponse(
        name="search.html.j2", context={"request": request, "search_term": q}
    )


# @router.get("/client/component/home")
# @datastar_response
# async def handle_get_client_component_home():
#     app_state.logger.info("Loading home view...")
#     yield SSE.patch_elements(templates.get_template("home.html").render())


# @router.get("/client/component/footer")
# @datastar_response
# async def handle_get_client_component_footer():
#     app_state.logger.info("Loading footer view...")
#     yield SSE.patch_elements(templates.get_template("footer.html").render())


@router.get("/client/component/settings-content")
@datastar_response
async def handle_get_client_component_settings(datastar_signals: ReadSignals):
    app_state.logger.info("Loading settings view...")
    signals = handle_signals(datastar_signals)
    if signals.client_id in app_state.clients:
        client = app_state.clients[signals.client_id]
        print(f"Client {signals.client_id} settings: {client.downloader_settings}")
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
    else:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, returning empty settings."
        )


@router.get("/client/component/settings")
@datastar_response
async def handle_get_client_settings(datastar_signals: ReadSignals):
    app_state.logger.info("Sending client settings...")
    signals = handle_signals(datastar_signals)
    if signals.client_id in app_state.clients:
        client = app_state.clients[signals.client_id]
        print(f"Client {signals.client_id} settings: {client.downloader_settings}")
        yield SSE.patch_signals(
            {
                "downloader_settings": client.downloader_settings,
            }
        )
    else:
        app_state.logger.warning(
            f"Client {signals.client_id} not found, cannot update settings."
        )


@router.post("/client/component/settings")
@datastar_response
async def handle_post_client_settings(datastar_signals: ReadSignals):
    app_state.logger.info("Updating settings...")
    signals = handle_signals(datastar_signals)
    if signals.client_id in app_state.clients:
        client = app_state.clients[signals.client_id]
        client.downloader_settings = signals.downloader_settings
        print(f"Client {signals.client_id} settings: {client.downloader_settings}")
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
            f"Client {signals.client_id} not found, cannot update settings."
        )
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


# @router.get("/client/test")
# async def handle_get_client_component_test(request: Request):
#     app_state.logger.info("Loading test view...")
#     return templates.TemplateResponse(
#         name="test.html", context={"request": request, "name": "World"}
#     )


@router.get("/client/search")
@datastar_response
async def handle_get_client_search(datastar_signals: ReadSignals):
    app_state.logger.info("Loading search...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"Search term: {signals.search_term}")
    # is_valid = validate_search_term(signals.search_term)
    songs = get_search_results(signals.search_term)
    # yield SSE.patch_elements(
    #     f"""
    #         <span id="search-list">
    #             {songs}
    #         </span>
    #     """
    # )
    yield SSE.patch_elements(
        templates.get_template("search-list.html.j2").render(
            songs=songs,
        )
    )


# @router.get("/client/home/input/rotating-placeholder")
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
    try:
        while True:
            t = templates.get_template(
                "search-input-rotating-placeholder.html.j2"
            ).render(placeholder_item=placeholder_items[index])
            yield SSE.patch_elements(t)
            await asyncio.sleep(5)
            index += 1
            if index >= len(placeholder_items):
                index = 0
    finally:
        app_state.logger.info("Unloading rotating-placeholder...")
