from abc import ABC
from abc import abstractmethod
from collections.abc import Sequence

class StreamsBase(Sequence):
    @abstractmethod
    def __init__(self, streams):
        """
        This method must parse audio streams into a list of
        dictionaries with the keys:
        "bitrate", "download_url", "encoding", "filesize".

        The list should typically be sorted in descending order
        based on the audio stream's bitrate.

        This sorted list must be assigned to ``self.streams``.
        """

        self.streams = streams

    def __repr__(self):
        return "Streams({})".format(self.streams)

    def __len__(self):
        return len(self.streams)

    def __getitem__(self, index):
        return self.streams[index]

    def __eq__(self, instance):
        return self.streams == instance.streams

    def getbest(self):
        """
        Returns the audio stream with the highest bitrate.
        """

        return self.streams[0]

    def getworst(self):
        """
        Returns the audio stream with the lowest bitrate.
        """

        return self.streams[-1]


class ProviderBase(ABC):
    def set_credentials(self, client_id, client_secret):
        """
        This method may or not be used depending on whether the
        metadata provider requires authentication or not.
        """

        raise NotImplementedError

    @abstractmethod
    def from_url(self, url):
        """
        Fetches metadata for the given URL.

        Parameters
        ----------
        url: `str`
            Media URL.

        Returns
        -------
        metadata: `dict`
            A *dict* of standardized metadata.
        """

        pass

    def from_query(self, query):
        """
        Fetches metadata for the given search query.

        Parameters
        ----------
        query: `str`
            Search query.

        Returns
        -------
        metadata: `dict`
            A *dict* of standardized metadata.
        """

        raise NotImplementedError

    @abstractmethod
    def _metadata_to_standard_form(self, metadata):
        """
        Transforms the metadata into a format consistent with all other
        metadata providers, for easy utilization.
        """

        pass

