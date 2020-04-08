from spotdl.lyrics import LyricBase

import pytest


class TestAbstractBaseClass:
    def test_error_abstract_base_class_lyricbase(self):
        with pytest.raises(TypeError):
            # This abstract base class must be inherited from
            # for instantiation
            LyricBase()

    def test_inherit_abstract_base_class_encoderbase(self):
        class LyricKid(LyricBase):
            def from_query(self, query):
                raise NotImplementedError

            def from_artist_and_track(self, artist, track):
                pass

            def from_url(self, url):
                raise NotImplementedError

        LyricKid()
