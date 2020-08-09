from spotdl.metadata import ProviderBase
from spotdl.metadata import StreamsBase

import pytest

class TestStreamsBaseABC:
    def test_error_abstract_base_class_streamsbase(self):
        with pytest.raises(TypeError):
            # This abstract base class must be inherited from
            # for instantiation
            StreamsBase()

    def test_inherit_abstract_base_class_streamsbase(self):
        class StreamsKid(StreamsBase):
            def __init__(self, streams):
                super().__init__(streams)

        streams = ("stream1", "stream2", "stream3")
        kid = StreamsKid(streams)
        assert kid.streams == streams


class TestMethods:
    class StreamsKid(StreamsBase):
        def __init__(self, streams):
            super().__init__(streams)


    @pytest.fixture(scope="module")
    def streamskid(self):
        streams = ("stream1", "stream2", "stream3")
        streamskid = self.StreamsKid(streams)
        return streamskid

    def test_getbest(self, streamskid):
        best_stream = streamskid.getbest()
        assert best_stream == "stream1"

    def test_getworst(self, streamskid):
        worst_stream = streamskid.getworst()
        assert worst_stream == "stream3"


class TestProviderBaseABC:
    def test_error_abstract_base_class_providerbase(self):
        with pytest.raises(TypeError):
            # This abstract base class must be inherited from
            # for instantiation
            ProviderBase()

    def test_inherit_abstract_base_class_providerbase(self):
        class ProviderKid(ProviderBase):
            def from_url(self, query):
                pass

            def _metadata_to_standard_form(self, metadata):
                pass

        ProviderKid()

