from spotdl import patcher
import pafy

import pytest

pafy_patcher = patcher.PatchPafy()
pafy_patcher.patch_getbestthumb()

class TestPafyContentAvailable:
    pass


class TestMethodAssignment:
    def test_pafy_getbestthumb(self):
        pafy.backend_shared.BasePafy.getbestthumb == patcher._getbestthumb


class TestMethodCalls:
    @pytest.fixture(scope="module")
    def content_fixture(self):
        content = pafy.new("http://youtube.com/watch?v=3nQNiWdeH2Q")
        return content

    def test_pafy_getbestthumb(self, content_fixture):
        thumbnail = patcher._getbestthumb(content_fixture)
        assert thumbnail == "https://i.ytimg.com/vi/3nQNiWdeH2Q/maxresdefault.jpg"

    def test_pafy_getbestthumb_without_ytdl(self, content_fixture):
        content_fixture._ydl_info["thumbnails"][0]["url"] = None
        thumbnail = patcher._getbestthumb(content_fixture)
        assert thumbnail == "https://i.ytimg.com/vi/3nQNiWdeH2Q/maxresdefault.jpg"


    def test_pafy_content_available(self):
        TestPafyContentAvailable._content_available = patcher._content_available
        assert TestPafyContentAvailable()._content_available("https://youtube.com/")
