from abc import ABC
from abc import abstractmethod

class StreamsBase(ABC):
    @abstractmethod
    def __init__(self, streams):
        """
        This method must parse audio streams into a list of
        dictionaries with the keys:
        "bitrate", "download_url", "encoding", "filesize".

        The list should typically be sorted in descending order
        based on the audio stream's bitrate.

        This sorted list must be assigned to `self.all`.
        """
        self.all = streams

    def getbest(self):
        """
        This method must return the audio stream with the
        highest bitrate.
        """
        return self.all[0]

    def getworst(self):
        """
        This method must return the audio stream with the
        lowest bitrate.
        """
        return self.all[-1]


class ProviderBase(ABC):
    def set_credentials(self, client_id, client_secret):
        """
        This method may or not be used depending on
        whether the metadata provider requires authentication
        or not.
        """
        pass

    @abstractmethod
    def from_url(self, url):
        """
        This method must return track metadata from the
        corresponding Spotify URL.
        """
        pass

    def from_query(self, query):
        """
        This method must return track metadata from the
        corresponding search query.
        """
        raise NotImplementedError

    @abstractmethod
    def metadata_to_standard_form(self, metadata):
        """
        This method must transform the fetched metadata
        into a format consistent with all other metadata
        providers, for easy utilization.
        """
        pass

