from spotdl.utils.downloader import check_ytmusic_connection


def test_check_ytmusic_connection_suppresses_empty_search_log(mocker):
    ytm = mocker.Mock()
    ytm.get_results.return_value = []
    mocker.patch("spotdl.utils.downloader.YouTubeMusic", return_value=ytm)

    assert check_ytmusic_connection() is False
    ytm.get_results.assert_called_once_with("a", log_search_failures=False)
