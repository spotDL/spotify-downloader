import pafy

from spotdl import internals


def _getbestthumb(self):
    url = self._ydl_info["thumbnails"][0]["url"]
    if url:
        return url

    part_url = "https://i.ytimg.com/vi/%s/" % self.videoid
    # Thumbnail resolution sorted in descending order
    thumbs = ("maxresdefault.jpg",
              "sddefault.jpg",
              "hqdefault.jpg",
              "mqdefault.jpg",
              "default.jpg")
    for thumb in thumbs:
        url = part_url + thumb
        if self._content_available(url):
            return url


@classmethod
def _content_available(cls, url):
    return internals.content_available(url)

def patch_pafy():
    pafy.backend_shared.BasePafy._bestthumb = None
    pafy.backend_shared.BasePafy._content_available = _content_available
    pafy.backend_shared.BasePafy.getbestthumb = _getbestthumb
