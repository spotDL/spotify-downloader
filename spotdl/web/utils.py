"""
Module for handling client signals.
"""

import inspect
from typing import Any, Awaitable, Callable, Optional

from datastar_py.fastapi import DatastarResponse
from datastar_py.fastapi import datastar_response as _datastar_response

from spotdl.types.options import DownloaderOptions
from spotdl.utils.web import app_state


class Signals:
    """
    Class that holds the client datastar signals.
    """

    client_id: str = ""
    search_term: str = ""
    downloader_settings: Optional["DownloaderOptions"] = None
    song_url: str = ""


def handle_signals(datastar_signals: dict | None) -> Signals:
    """
    Handle the signals received from the client.
    This function can be used to process or validate the signals before they are used.
    """
    app_state.logger.debug(f"Received signals: {datastar_signals}")
    if not datastar_signals:
        # raise ValueError("No signals provided.")
        app_state.logger.warning("No signals provided, returning empty Signals.")
        return Signals()
    signals = Signals()
    signals.client_id = datastar_signals.get("client_id", "")
    signals.search_term = datastar_signals.get("search_term", "")
    signals.downloader_settings = datastar_signals.get("downloader_settings")
    signals.song_url = datastar_signals.get("song_url", "")
    return signals


def datastar_response(
    func: Callable[..., Any],
) -> Callable[..., Awaitable[DatastarResponse]]:
    """
    Wrap a route handler's result in a DatastarResponse.

    datastar_py's decorator uses functools.wraps, so newer FastAPI versions
    follow __wrapped__ to the original async generator and try to stream it
    as JSON Lines instead of awaiting the wrapper, which crashes every
    datastar route. Keep the handler's signature so FastAPI still sees its
    parameters, but drop __wrapped__.

    Without __wrapped__, FastAPI resolves string annotations against the
    wrapper's module, so resolve them here against the handler's module. The
    return annotation is DatastarResponse so FastAPI doesn't build a response
    model from the handler's own return annotation.

    ### Arguments
    - func: The route handler, a function or generator function.

    ### Returns
    - returns the wrapped route handler.
    """

    wrapper = _datastar_response(func)
    wrapper.__signature__ = inspect.signature(  # type: ignore[attr-defined]
        func, eval_str=True
    ).replace(return_annotation=DatastarResponse)
    del wrapper.__wrapped__  # type: ignore[attr-defined]

    return wrapper
