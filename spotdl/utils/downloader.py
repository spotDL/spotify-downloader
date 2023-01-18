from spotdl.providers.audio import YouTubeMusic


def check_ytmusic_connection() -> bool:
    """
    Check if we can connect to YouTube Music API

    ### Returns
    - `True` if we can connect to YouTube Music API
    - `False` if we can't connect to YouTube Music API
    """

    # Check if we are getting results from YouTube Music
    ytm = YouTubeMusic()
    test_results = ytm.get_results("a")
    if len(test_results) == 0:
        return False

    return True
