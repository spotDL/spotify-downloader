import os

from abc import ABC
from abc import abstractmethod

class EmbedderBase(ABC):
    """
    The subclass must define the supported media file encoding
    formats here using a static variable - such as:

    >>> supported_formats = ("mp3", "opus", "flac")
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

    def apply_metadata(self, path, metadata, encoding=None):
        """
        This method must automatically detect the media encoding
        format from file path and embed the corresponding metadata
        on the given file by calling an appropriate submethod.
        """
        if encoding is None:
            encoding = self.get_encoding(path)
        if encoding not in self.supported_formats:
            raise TypeError(
                'The input format ("{}") is not supported.'.format(
                encoding,
            ))
        embed_on_given_format = self.targets[encoding]
        embed_on_given_format(path, metadata)

    def as_mp3(self, path, metadata):
        """
        Method for mp3 support. This method might be defined in
        a subclass.

        Other methods for additional supported formats must also
        be declared here.
        """
        raise NotImplementedError

    def as_opus(self, path, metadata):
        """
        Method for opus support. This method might be defined in
        a subclass.

        Other methods for additional supported formats must also
        be declared here.
        """
        raise NotImplementedError

    def as_flac(self, path, metadata):
        """
        Method for flac support. This method might be defined in
        a subclass.

        Other methods for additional supported formats must also
        be declared here.
        """
        raise NotImplementedError

