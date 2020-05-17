import os

from abc import ABC
from abc import abstractmethod

import urllib.request

class EmbedderBase(ABC):
    """
    The subclass must define the supported media file encoding
    formats here using a static variable - such as:

    >>> supported_formats = ("mp3", "m4a", "flac")
    """
    supported_formats = ()

    @abstractmethod
    def __init__(self):
        """
        For every supported format, there must be a corresponding
        method that applies metadata on this format.

        Such as if mp3 is supported, there must exist a method named
        `as_mp3` on this class that applies metadata on mp3 files.
        """
        # self.targets = { fmt: eval(str("self.as_" + fmt))
        #                  for fmt in self.supported_formats }
        #
        # TODO: The above code seems to fail for some reason
        #       I do not know.
        self.targets = {}
        for fmt in self.supported_formats:
            # FIXME: Calling `eval` is dangerous here!
            self.targets[fmt] = eval("self.as_" + fmt)

    def get_encoding(self, path):
        """
        This method must determine the encoding for a local
        audio file. Such as "mp3", "wav", "m4a", etc.
        """
        _, extension = os.path.splitext(path)
        # Ignore the initial dot from file extension
        return extension[1:]

    def apply_metadata(self, path, metadata, cached_albumart=None, encoding=None):
        """
        This method must automatically detect the media encoding
        format from file path and embed the corresponding metadata
        on the given file by calling an appropriate submethod.
        """
        if cached_albumart is None:
            cached_albumart = urllib.request.urlopen(
                metadata["album"]["images"][0]["url"],
            ).read()
        if encoding is None:
            encoding = self.get_encoding(path)
        if encoding not in self.supported_formats:
            raise TypeError(
                'The input format ("{}") is not supported.'.format(
                encoding,
            ))
        embed_on_given_format = self.targets[encoding]
        embed_on_given_format(path, metadata, cached_albumart=cached_albumart)

    def as_mp3(self, path, metadata, cached_albumart=None):
        """
        Method for mp3 support. This method might be defined in
        a subclass.

        Other methods for additional supported formats must also
        be declared here.
        """
        raise NotImplementedError

    def as_m4a(self, path, metadata, cached_albumart=None):
        """
        Method for m4a support. This method might be defined in
        a subclass.

        Other methods for additional supported formats must also
        be declared here.
        """
        raise NotImplementedError

    def as_flac(self, path, metadata, cached_albumart=None):
        """
        Method for flac support. This method might be defined in
        a subclass.

        Other methods for additional supported formats must also
        be declared here.
        """
        raise NotImplementedError

