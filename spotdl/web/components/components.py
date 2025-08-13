import asyncio
from multiprocessing import context
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
from spotdl.utils.web import app_state
from spotdl.web.utils import handle_signals


router = APIRouter()
# env = jinja2.Environment(loader=jinja2.FileSystemLoader("spotdl/web/components"))
templates = Jinja2Templates(directory="spotdl/web/components")


@router.get("/client/component/home")
@datastar_response
async def handle_get_client_component_home():
    app_state.logger.info("Loading home view...")
    yield SSE.patch_elements(templates.get_template("home.html").render())


@router.get("/client/component/footer")
@datastar_response
async def handle_get_client_component_footer():
    app_state.logger.info("Loading footer view...")
    yield SSE.patch_elements(templates.get_template("footer.html").render())


@router.get("/client/component/settings-content")
@datastar_response
async def handle_get_client_component_settings(datastar_signals: ReadSignals):
    app_state.logger.info("Loading settings view...")
    app_state.logger.info(f"Received signals: {datastar_signals}")
    signals = handle_signals(datastar_signals)
    if signals.client_id in app_state.clients:
        client = app_state.clients[signals.client_id]
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


@router.get("/client/test")
async def handle_get_client_component_test(request: Request):
    app_state.logger.info("Loading test view...")
    return templates.TemplateResponse(
        name="test.html", context={"request": request, "name": "World"}
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
