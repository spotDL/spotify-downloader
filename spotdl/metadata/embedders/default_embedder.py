from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TORY, TYER, TPUB, APIC, USLT, COMM
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import Picture, FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

import urllib.request
import base64

from spotdl.metadata import EmbedderBase
from spotdl.metadata import BadMediaFileError

import logging
logger = logging.getLogger(__name__)

# Apple has specific tags - see mutagen docs -
# http://mutagen.readthedocs.io/en/latest/api/mp4.html
M4A_TAG_PRESET = {
    "album": "\xa9alb",
    "artist": "\xa9ART",
    "date": "\xa9day",
    "title": "\xa9nam",
    "year": "\xa9day",
    "originaldate": "purd",
    "comment": "\xa9cmt",
    "group": "\xa9grp",
    "writer": "\xa9wrt",
    "genre": "\xa9gen",
    "tracknumber": "trkn",
    "albumartist": "aART",
    "discnumber": "disk",
    "cpil": "cpil",
    "albumart": "covr",
    "copyright": "cprt",
    "tempo": "tmpo",
    "lyrics": "\xa9lyr",
    "comment": "\xa9cmt",
    "explicit": "rtng",
}

TAG_PRESET = {}
for key in M4A_TAG_PRESET.keys():
    TAG_PRESET[key] = key


class EmbedderDefault(EmbedderBase):
    """
    A class for applying metadata on media files.

    Examples
    --------
    - Applying metadata on an already downloaded MP3 file:

        >>> from spotdl.metadata_search import MetadataSearch
        >>> provider = MetadataSearch("ncs spectre")
        >>> metadata = provider.on_youtube()
        >>> from spotdl.metadata.embedders import EmbedderDefault
        >>> embedder = EmbedderDefault()
        >>> embedder.as_mp3("media.mp3", metadata)
    """
    supported_formats = ("mp3", "m4a", "flac", "ogg", "opus")

    def __init__(self):
        super().__init__()
        self._m4a_tag_preset = M4A_TAG_PRESET
        self._tag_preset = TAG_PRESET
        # self.provider = "spotify" if metadata["spotify_metadata"] else "youtube"
    def as_mp3(self, path, metadata, cached_albumart=None):
        """
        Apply metadata on MP3 media files.

        Parameters
        ----------
        path: `str`
            Path to the media file.

        metadata: `dict`
            Metadata (standardized) to apply to the media file.

        cached_albumart: `bool`
            An albumart image binary. If passed, the albumart URL
            present in the ``metadata`` won't be downloaded or used.
        """
        logger.debug('Writing MP3 metadata to "{path}".'.format(path=path))
        # EasyID3 is fun to use ;)
        # For supported easyid3 tags:
        # https://github.com/quodlibet/mutagen/blob/master/mutagen/easyid3.py
        # Check out somewhere at end of above linked file
        audiofile = EasyID3(path)
        self._embed_basic_metadata(audiofile, metadata, "mp3", preset=TAG_PRESET)
        audiofile["media"] = metadata["type"]
        audiofile["author"] = metadata["artists"][0]["name"]
        audiofile["lyricist"] = metadata["artists"][0]["name"]
        audiofile["arranger"] = metadata["artists"][0]["name"]
        audiofile["performer"] = metadata["artists"][0]["name"]
        provider = metadata["provider"]
        audiofile["website"] = metadata["external_urls"][provider]
        audiofile["length"] = str(metadata["duration"])
        if metadata["publisher"]:
            audiofile["encodedby"] = metadata["publisher"]
        if metadata["external_ids"]["isrc"]:
            audiofile["isrc"] = metadata["external_ids"]["isrc"]
        audiofile.save(v2_version=3)

        # For supported id3 tags:
        # https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_frames.py
        # Each class in the linked source file represents an id3 tag
        audiofile = ID3(path)
        if metadata["year"]:
            audiofile["TORY"] = TORY(encoding=3, text=metadata["year"])
            audiofile["TYER"] = TYER(encoding=3, text=metadata["year"])
        if metadata["publisher"]:
            audiofile["TPUB"] = TPUB(encoding=3, text=metadata["publisher"])
        provider = metadata["provider"]
        audiofile["COMM"] = COMM(
            encoding=3, text=metadata["external_urls"][provider]
        )
        if metadata["lyrics"]:
            audiofile["USLT"] = USLT(
                encoding=3, desc=u"Lyrics", text=metadata["lyrics"]
            )
        if cached_albumart is None:
            cached_albumart = urllib.request.urlopen(
                metadata["album"]["images"][0]["url"]
            ).read()
        try:
            audiofile["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc=u"Cover",
                data=cached_albumart,
            )
        except IndexError:
            pass

        audiofile.save(v2_version=3)

    def as_m4a(self, path, metadata, cached_albumart=None):
        """
        Apply metadata on FLAC media files.

        Parameters
        ----------
        path: `str`
            Path to the media file.

        metadata: `dict`
            Metadata (standardized) to apply to the media file.

        cached_albumart: `bool`
            An albumart image binary. If passed, the albumart URL
            present in the ``metadata`` won't be downloaded or used.
        """

        logger.debug('Writing M4A metadata to "{path}".'.format(path=path))
        # For supported m4a tags:
        # https://github.com/quodlibet/mutagen/blob/master/mutagen/mp4/__init__.py
        # Look for the class named `MP4Tags` in the linked source file
        audiofile = MP4(path)
        self._embed_basic_metadata(audiofile, metadata, "m4a", preset=M4A_TAG_PRESET)
        if metadata["year"]:
            audiofile[M4A_TAG_PRESET["year"]] = metadata["year"]
        provider = metadata["provider"]
        audiofile[M4A_TAG_PRESET["comment"]] = metadata["external_urls"][provider]
        if metadata["lyrics"]:
            audiofile[M4A_TAG_PRESET["lyrics"]] = metadata["lyrics"]
        # Explicit values: Dirty: 4, Clean: 2, None: 0
        audiofile[M4A_TAG_PRESET["explicit"]] = (4,) if metadata["explicit"] else (2,)
        try:
            if cached_albumart is None:
                cached_albumart = urllib.request.urlopen(
                    metadata["album"]["images"][0]["url"]
                ).read()
            audiofile[M4A_TAG_PRESET["albumart"]] = [
                MP4Cover(cached_albumart, imageformat=MP4Cover.FORMAT_JPEG)
            ]
        except IndexError:
            pass

        audiofile.save()

    def as_flac(self, path, metadata, cached_albumart=None):
        """
        Apply metadata on MP3 media files.

        Parameters
        ----------
        path: `str`
            Path to the media file.

        metadata: `dict`
            Metadata (standardized) to apply to the media file.

        cached_albumart: `bool`
            An albumart image binary. If passed, the albumart URL
            present in the ``metadata`` won't be downloaded or used.
        """

        logger.debug('Writing FLAC metadata to "{path}".'.format(path=path))
        # For supported flac tags:
        # https://github.com/quodlibet/mutagen/blob/master/mutagen/mp4/__init__.py
        # Look for the class named `MP4Tags` in the linked source file
        audiofile = FLAC(path)

        self._embed_basic_metadata(audiofile, metadata, "flac")
        self._embed_ogg_metadata(audiofile, metadata)
        self._embed_mbp_picture(audiofile, "metadata", cached_albumart, "flac")

        audiofile.save()

    def as_ogg(self, path, metadata, cached_albumart=None):
        logger.debug('Writing OGG Vorbis metadata to "{path}".'.format(path=path))
        audiofile = OggVorbis(path)

        self._embed_basic_metadata(audiofile, metadata, "ogg")
        self._embed_ogg_metadata(audiofile, metadata)
        self._embed_mbp_picture(audiofile, metadata, cached_albumart, "ogg")

        audiofile.save()

    def as_opus(self, path, metadata, cached_albumart=None):
        logger.debug('Writing Opus metadata to "{path}".'.format(path=path))
        audiofile = OggOpus(path)

        self._embed_basic_metadata(audiofile, metadata, "opus")
        self._embed_ogg_metadata(audiofile, metadata)
        self._embed_mbp_picture(audiofile, metadata, cached_albumart, "opus")

        audiofile.save()

    def _embed_ogg_metadata(self, audiofile, metadata):
        if metadata["year"]:
            audiofile["year"] = metadata["year"]
        provider = metadata["provider"]
        audiofile["comment"] = metadata["external_urls"][provider]
        if metadata["lyrics"]:
            audiofile["lyrics"] = metadata["lyrics"]

    def _embed_mbp_picture(self, audiofile, metadata, cached_albumart, encoding):
        image = Picture()
        image.type = 3
        image.desc = "Cover"
        image.mime = "image/jpeg"
        if cached_albumart is None:
            cached_albumart = urllib.request.urlopen(
                metadata["album"]["images"][0]["url"]
            ).read()
        image.data = cached_albumart

        if encoding == "flac":
            audiofile.add_picture(image)
        elif encoding == "ogg" or encoding == "opus":
            # From the Mutagen docs (https://mutagen.readthedocs.io/en/latest/user/vcomment.html)
            image_data = image.write()
            encoded_data = base64.b64encode(image_data)
            vcomment_value = encoded_data.decode("ascii")
            audiofile["metadata_block_picture"] = [vcomment_value]

    def _embed_basic_metadata(self, audiofile, metadata, encoding, preset=TAG_PRESET):
        audiofile[preset["artist"]] = metadata["artists"][0]["name"]
        if metadata["album"]["artists"][0]["name"]:
            audiofile[preset["albumartist"]] = metadata["album"]["artists"][0]["name"]
        if metadata["album"]["name"]:
            audiofile[preset["album"]] = metadata["album"]["name"]
        audiofile[preset["title"]] = metadata["name"]
        if metadata["release_date"]:
            audiofile[preset["date"]] = metadata["release_date"]
            audiofile[preset["originaldate"]] = metadata["release_date"]
        if metadata["genre"]:
            audiofile[preset["genre"]] = metadata["genre"]
        if metadata["copyright"]:
            audiofile[preset["copyright"]] = metadata["copyright"]
        if encoding == "flac" or encoding == "ogg" or encoding == "opus":
            audiofile[preset["discnumber"]] = str(metadata["disc_number"])
        else:
            audiofile[preset["discnumber"]] = [(metadata["disc_number"], 0)]
        zfilled_track_number = str(metadata["track_number"]).zfill(len(str(metadata["total_tracks"])))
        if encoding == "flac" or encoding == "ogg" or encoding == "opus":
            audiofile[preset["tracknumber"]] = zfilled_track_number
        else:
            if preset["tracknumber"] == TAG_PRESET["tracknumber"]:
                audiofile[preset["tracknumber"]] = "{}/{}".format(
                    zfilled_track_number, metadata["total_tracks"]
                )
            else:
                audiofile[preset["tracknumber"]] = [
                    (metadata["track_number"], metadata["total_tracks"])
                ]

