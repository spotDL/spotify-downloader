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
from spotdl.utils.web import validate_search_term

__all__ = ["router"]

router = APIRouter()


@router.get("/client/load")
async def handle_get_client_load():
    print("Loading client...")
    return None


@router.get("/client/goto/home")
async def handle_get_client_goto_home():
    print("Loading home view...")
    return None


@router.get("/client/search")
@datastar_response
async def handle_get_client_search(signals: ReadSignals):
    print("Loading search...")
    # signals = await read_signals(signals)
    print(f"Search term: {signals.get('searchTerm', '')}")

    yield SSE.patch_elements(
        """
        <button id="search-button" class="btn btn-square btn-primary loading">
        </button>
        """
    )
    await asyncio.sleep(1)
    search_term = signals.get("searchTerm", "")
    is_valid = validate_search_term(search_term)
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


@router.get("/client/rotating-placeholder")
@datastar_response
async def handle_client_rotating_placeholder(signals: ReadSignals):
    print("Loading rotating-placeholder...")
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
        yield SSE.patch_elements(f"""
                                 <input id="input-rotating-placeholder" type="text" placeholder="{placeholder_items[index]}" class="input input-bordered w-full text-base-content" data-bind="searchTerm" data-on-keyup.enter="@get('/client/search')" />""")
        await asyncio.sleep(5)
        index += 1
        if index >= len(placeholder_items):
            index = 0
