from spotdl.utils.web import app_state


class Signals:
    """
    Class that holds the client datastar signals.
    """

    client_id: str = ""
    search_term: str = ""
    downloader_settings: dict = {}
    song_url: str = ""


def handle_signals(datastar_signals: dict) -> Signals:
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
    signals.downloader_settings = datastar_signals.get("downloader_settings", {})
    signals.song_url = datastar_signals.get("song_url", "")
    return signals
