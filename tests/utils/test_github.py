import pytest

from spotdl import _version
from spotdl.utils.github import (
    WEB_APP_URL,
    check_for_updates,
    create_github_url,
    download_github_dir,
    get_status,
)

from unittest.mock import patch
from spotdl import _version
from spotdl.utils.github import (
    WEB_APP_URL,
    check_for_updates,
    create_github_url,
    download_github_dir,
    get_status,
    RateLimitError,
)

@pytest.mark.vcr()
def test_get_status():
    status = get_status("master", "dev", "spotdl/spotify-downloader")

    assert None not in status


@pytest.mark.vcr()
def test_get_status_fail():
    with pytest.raises(RuntimeError):
        get_status("master", "dev", "spotdl/spotify-downloader-fail")


@pytest.mark.vcr()
def test_check_for_updates(monkeypatch):
    monkeypatch.setattr(_version, "__version__", "3.9.4")
    message = check_for_updates("spotdl/spotify-downloader")

    assert message != ""


@pytest.mark.vcr()
def test_check_for_updates_fail(monkeypatch):
    monkeypatch.setattr(_version, "__version__", "3.9.4")
    with pytest.raises(RuntimeError):
        check_for_updates("spotdl/spotify-downloader-fail")


@pytest.mark.vcr()
def test_create_github_url():
    url = create_github_url(WEB_APP_URL)

    assert url == "https://api.github.com/repos/spotdl/web-ui/contents/dist?ref=master"


@pytest.mark.vcr()
def test_download_github_dir(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    download_github_dir(WEB_APP_URL, False)
    download_dir = tmpdir.listdir()[0]
    assert download_dir.isdir() is True
    assert download_dir.join("index.html").isfile() is True

####################################################


@patch('spotdl.utils.github.requests.get')
def test_get_status_rate_limit(mock_get):
    mock_get.return_value.status_code = 403
    with pytest.raises(RateLimitError):
        get_status("master", "dev", "spotdl/spotify-downloader")


# @patch('spotdl.utils.github.get_latest_version')
# def test_check_for_updates_rate_limit(mock_get_latest_version, monkeypatch):
#     monkeypatch.setattr(_version, "__version__", "3.9.4")
#     mock_get_latest_version.side_effect = RateLimitError
#     message = check_for_updates("spotdl/spotify-downloader")
#     assert "GitHub API rate limit exceeded" in message


def test_create_github_url_invalid():
    with pytest.raises(ValueError):
        create_github_url("https://github.com/spotdl")


@patch('spotdl.utils.github.requests.get')
def test_download_github_dir_rate_limit(mock_get, tmpdir):
    mock_get.return_value.json.return_value = {"message": "API rate limit exceeded"}
    result = download_github_dir(WEB_APP_URL, False, tmpdir)
    assert result is None


# @patch('spotdl.utils.github.requests.get')
# def test_download_github_dir_flat(mock_get, tmpdir):
#     mock_get.return_value.json.return_value = [
#         {"path": "file1.txt", "download_url": "http://example.com/file1.txt", "type": "file"},
#     ]
#     download_github_dir(WEB_APP_URL, True, tmpdir)
#     assert tmpdir.join("file1.txt").isfile() is True
