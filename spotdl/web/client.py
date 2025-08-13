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
from fastapi import APIRouter, Request
from spotdl.utils.web import validate_search_term

import spotdl.web.components.components as components
import spotdl.web.api as api

from spotdl.utils.web import Client, app_state
import uuid

from spotdl.web.utils import handle_signals

__all__ = ["router"]

router = APIRouter()

router.include_router(components.router)


@router.get("/client/load")
@datastar_response
async def handle_get_client_load(datastar_signals: ReadSignals):
    app_state.logger.info("Loading client...")
    signals = handle_signals(datastar_signals)
    if not signals.client_id:
        app_state.logger.warning("No client ID provided, generating a new one.")
        # Generate a new client ID if not provided
        signals.client_id = uuid.uuid4().hex
    client = Client(signals.client_id)
    await client.connect()

    # First send the client ID and then the home template.
    yield SSE.patch_elements("""<div id="banner"></div>""")
    yield SSE.patch_signals(
        {
            "client_id": client.client_id,
        }
    )
    yield SSE.patch_elements(
        f'<span id="router-view">{components.templates.get_template("home.html").render()}</span>'
    )


@router.get("/client/updates")
@datastar_response
async def handle_get_client_updates(datastar_signals: ReadSignals):
    signals = handle_signals(datastar_signals)
    client = Client(signals.client_id)
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


@router.get("/client/search")
@datastar_response
async def handle_get_client_search(datastar_signals: ReadSignals):
    app_state.logger.info("Loading search...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"Search term: {signals.search_term}")

    yield SSE.patch_elements(
        """
        <button id="search-button" class="btn btn-square btn-primary loading">
        </button>
        """
    )
    await asyncio.sleep(1)
    is_valid = validate_search_term(signals.search_term)
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


# @datastar_response
@router.get("/client/update-settings")
async def handle_get_client_update_settings(datastar_signals: ReadSignals):
    app_state.logger.info("Updating settings...")
    signals = handle_signals(datastar_signals)
    app_state.logger.info(f"Updating settings for client: {signals.client_id}")
    if signals.client_id in app_state.clients:
        client = app_state.clients[signals.client_id]
        # Update the client's settings here if needed
        # For example, you could update the client's search term or other settings
        # client.search_term = signals.search_term
        client.downloader_settings = signals.downloader_settings
        app_state.logger.info(f"Updated settings for client: {client.client_id}")
    else:
        app_state.logger.warning(f"Client {signals.client_id} not found.")
