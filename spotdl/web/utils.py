from datastar_py.fastapi import (
    ReadSignals,
)
from spotdl.utils.web import app_state


class Signals:
    """
    Class that holds the client datastar signals.
    """

    clientId: str = ""
    searchTerm: str = ""
    downloader_settings: dict = {}


def handle_signals(datastar_signals: dict) -> Signals:
    """
    Handle the signals received from the client.
    This function can be used to process or validate the signals before they are used.
    """
    app_state.logger.info(f"Received signals: {datastar_signals}")
    if not datastar_signals:
        # raise ValueError("No signals provided.")
        app_state.logger.warning("No signals provided, returning empty Signals.")
        return Signals()
    signals = Signals()
    signals.clientId = datastar_signals.get("clientId", "")
    signals.searchTerm = datastar_signals.get("searchTerm", "")
    signals.downloader_settings = datastar_signals.get("downloader_settings", {})
    return signals
