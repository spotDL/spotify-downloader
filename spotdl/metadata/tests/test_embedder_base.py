from spotdl.metadata import EmbedderBase

import pytest

class EmbedderKid(EmbedderBase):
    def __init__(self):
        super().__init__()


class TestEmbedderBaseABC:
    def test_error_base_class_embedderbase(self):
        with pytest.raises(TypeError):
            # This abstract base class must be inherited from
            # for instantiation
            EmbedderBase()

    def test_inherit_abstract_base_class_streamsbase(self):
        EmbedderKid()


class TestMethods:
    @pytest.fixture(scope="module")
    def embedderkid(self):
        return EmbedderKid()

    def test_target_formats(self, embedderkid):
        assert embedderkid.supported_formats == ()

    @pytest.mark.parametrize("path, expect_encoding", (
        ("/a/b/c/file.mp3", "mp3"),
        ("music/pop/1.wav", "wav"),
        ("/a path/with spaces/track.m4a", "m4a"),
    ))
    def test_get_encoding(self, embedderkid, path, expect_encoding):
        assert embedderkid.get_encoding(path) == expect_encoding

    def test_apply_metadata_with_explicit_encoding(self, embedderkid):
        with pytest.raises(TypeError):
            embedderkid.apply_metadata("/path/to/music.mp3", {}, cached_albumart="imagedata", encoding="mp3")

    def test_apply_metadata_with_implicit_encoding(self, embedderkid):
        with pytest.raises(TypeError):
            embedderkid.apply_metadata("/path/to/music.wav", {}, cached_albumart="imagedata")

    class MockHTTPResponse:
        """
        This mocks `urllib.request.urlopen` for custom response text.
        """
        response_file = ""

        def __init__(self, url):
            pass

        def read(self):
            pass

    def test_apply_metadata_without_cached_image(self, embedderkid, monkeypatch):
        monkeypatch.setattr("urllib.request.urlopen", self.MockHTTPResponse)
        metadata = {"album": {"images": [{"url": "http://animageurl.com"},]}}
        with pytest.raises(TypeError):
            embedderkid.apply_metadata("/path/to/music.wav", metadata, cached_albumart=None)

    @pytest.mark.parametrize("fmt_method_suffix", (
        "as_mp3",
        "as_m4a",
        "as_flac",
        "as_ogg",
        "as_opus",
    ))
    def test_embed_formats(self, fmt_method_suffix, embedderkid):
        method = eval("embedderkid." + fmt_method_suffix)
        with pytest.raises(NotImplementedError):
            method("/a/random/path", {})

