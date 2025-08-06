import asyncio
import time
from datastar_py.fastapi import (
    DatastarResponse,
    datastar_response,
    ReadSignals,
    read_signals,
    ServerSentEventGenerator as SSE,
)
from datastar_py.sse import DatastarEvent
from fastapi import APIRouter
from spotdl.utils.web import validate_search_term

# from components.home import router as home_router
import spotdl.web.components.home as home
import spotdl.web.api as api

from spotdl.utils.web import Client, app_state
import uuid

__all__ = ["router"]

router = APIRouter()

router.include_router(home.router)


class Signals:
    """
    Class that holds the client datastar signals.
    """

    clientId: str
    searchTerm: str = ""


def handle_signals(datastar_signals: ReadSignals) -> Signals:
    """
    Handle the signals received from the client.
    This function can be used to process or validate the signals before they are used.
    """
    app_state.logger.info(f"Received signals: {datastar_signals}")
    if not datastar_signals:
        raise ValueError(
            "No signals provided. Please provide 'year' and 'classification'."
        )
    signals = Signals()
    signals.clientId = datastar_signals.get("clientId", "")
    signals.searchTerm = datastar_signals.get("searchTerm", "")
    return signals


@router.get("/client/load")
@datastar_response
async def handle_get_client_load():
    app_state.logger.info("Loading client...")
    client = Client(uuid.uuid4().hex)
    await client.connect()
    yield SSE.patch_elements(home.page())
    yield SSE.patch_signals(
        {
            "clientId": client.client_id,
        }
    )
    """
    We are going to use Server-Sent Events (SSE) to update the time every 5 seconds.
    This will allow us to know when the client disconnected, as the time will stop updating.
    """
    try:
        while True:
            yield SSE.patch_elements(f"""<span id="time" >{time.time()}</span>""")
            await asyncio.sleep(5)
    finally:
        app_state.logger.info("Unloading client...")
        await client.disconnect()


@router.get("/client/goto/home")
@datastar_response
async def handle_get_client_goto_home():
    app_state.logger.info("Loading home view...")
    yield SSE.patch_elements(home.page())


@router.get("/client/search")
@datastar_response
async def handle_get_client_search(datastar_signals: ReadSignals):
    app_state.logger.info("Loading search...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"Search term: {signals.searchTerm}")

    yield SSE.patch_elements(
        """
        <button id="search-button" class="btn btn-square btn-primary loading">
        </button>
        """
    )
    await asyncio.sleep(1)
    is_valid = validate_search_term(signals.searchTerm)
    if is_valid:
        icon = "clarity:download-line"
    else:
        icon = "clarity:search-line"
    yield SSE.patch_elements(
        f"""
        <button id="search-button" class="btn btn-square btn-primary" data-on-click="@get('/client/search')">
            <iconify-icon icon="{icon}" style="font-size: 24px"></iconify-icon>
        </button>
        """
    )
