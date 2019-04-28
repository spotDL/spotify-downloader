from pafy import backend_youtube_dl
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

def _process_streams(self):
    for format_index in range(len(self._ydl_info['formats'])):
        try:
            self._ydl_info['formats'][format_index]['url'] = self._ydl_info['formats'][format_index]['fragment_base_url']
        except KeyError:
            pass
    return backend_youtube_dl.YtdlPafy._old_process_streams(self)

@classmethod
def _content_available(cls, url):
    return internals.content_available(url)


class PatchPafy:
    def patch_getbestthumb(self):
        pafy.backend_shared.BasePafy._bestthumb = None
        pafy.backend_shared.BasePafy._content_available = _content_available
        pafy.backend_shared.BasePafy.getbestthumb = _getbestthumb

    def patch_process_streams(self):
        backend_youtube_dl.YtdlPafy._old_process_streams = backend_youtube_dl.YtdlPafy._process_streams
        backend_youtube_dl.YtdlPafy._process_streams = _process_streams
