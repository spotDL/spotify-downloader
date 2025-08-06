import asyncio
from datastar_py.fastapi import (
    DatastarResponse,
    datastar_response,
    ReadSignals,
    read_signals,
    ServerSentEventGenerator as SSE,
)
from datastar_py.sse import DatastarEvent
from fastapi import APIRouter
import jinja2

from spotdl.utils.web import app_state


router = APIRouter()
templates = jinja2.Environment(loader=jinja2.FileSystemLoader("spotdl/web/components"))


def page():
    """
    Load the home view.
    """

    home = templates.get_template("home.html").render()

    return home


@router.get("/client/home/input/rotating-placeholder")
@datastar_response
async def handle_client_home_input_rotating_placeholder(signals: ReadSignals):
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
            yield SSE.patch_elements(f"""
                                    <input id="input-rotating-placeholder" type="text" placeholder="{placeholder_items[index]}" class="input input-bordered w-full text-base-content" data-bind="searchTerm" data-on-keyup.enter="@get('/client/search')" />""")
            await asyncio.sleep(5)
            index += 1
            if index >= len(placeholder_items):
                index = 0
    finally:
        app_state.logger.info("Unloading rotating-placeholder...")
