from spotdl.lyrics import LyricBase

import pytest


class TestAbstractBaseClass:
    def test_error_abstract_base_class_lyricbase(self):
        artist = "awesome artist"
        track = "amazing track"

        with pytest.raises(TypeError):
            # This abstract base class must be inherited from
            # for instantiation
            LyricBase(artist, track)


    def test_inherit_abstract_base_class_encoderbase(self):
        class LyricKid(LyricBase):
            def __init__(self, artist, track):
                super().__init__(artist, track)

            def get_lyrics(self):
                pass


        artist = "awesome artist"
        track = "amazing track"

        LyricKid(artist, track)
