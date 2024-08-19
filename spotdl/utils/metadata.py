"""
Module for embedding metadata into audio files using Mutagen.

```python
embed_metadata(
    output_file=Path("test.mp3"),
    song=song_object,
    file_format="mp3",
)
```
"""

import base64
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from mutagen._file import File
from mutagen.flac import Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import (
    APIC,
    COMM,
    POPM,
    SYLT,
    TALB,
    TCOM,
    TCON,
    TCOP,
    TDRC,
    TIT2,
    TPE1,
    TRCK,
    TSRC,
    TYER,
    USLT,
    WOAS,
)
from mutagen.id3._specs import Encoding
from mutagen.mp4 import MP4Cover
from mutagen.wave import WAVE

from spotdl.types.song import Song
from spotdl.utils.config import GlobalConfig
from spotdl.utils.formatter import to_ms
from spotdl.utils.lrc import remomve_lrc

logger = logging.getLogger(__name__)

__all__ = [
    "MetadataError",
    "M4A_TAG_PRESET",
    "MP3_TAG_PRESET",
    "TAG_PRESET",
    "TAG_TO_SONG",
    "M4A_TO_SONG",
    "MP3_TO_SONG",
    "LRC_REGEX",
    "embed_metadata",
    "embed_cover",
    "embed_lyrics",
    "get_file_metadata",
]


class MetadataError(Exception):
    """
    Base class for all exceptions related to metadata and id3 embedding.
    """


# Apple has specific tags - see mutagen docs -
# http://mutagen.readthedocs.io/en/latest/api/mp4.html
M4A_TAG_PRESET = {
    "album": "\xa9alb",
    "artist": "\xa9ART",
    "date": "\xa9day",
    "title": "\xa9nam",
    "year": "\xa9day",
    "comment": "\xa9cmt",
    "group": "\xa9grp",
    "writer": "\xa9wrt",
    "genre": "\xa9gen",
    "tracknumber": "trkn",
    "trackcount": "trkn",
    "albumartist": "aART",
    "discnumber": "disk",
    "disccount": "disk",
    "cpil": "cpil",
    "albumart": "covr",
    "encodedby": "\xa9too",
    "copyright": "cprt",
    "tempo": "tmpo",
    "lyrics": "\xa9lyr",
    "explicit": "rtng",
    "woas": "----:spotdl:WOAS",
    "isrc": "----:spotdl:ISRC",
}

MP3_TAG_PRESET = {
    "album": "TALB",
    "artist": "TPE1",
    "date": "TDRC",
    "title": "TIT2",
    "year": "TDRC",
    "comment": "COMM::XXX",
    "group": "TIT1",
    "writer": "TEXT",
    "genre": "TCON",
    "tracknumber": "TRCK",
    "trackcount": "TRCK",
    "albumartist": "TPE2",
    "discnumber": "TPOS",
    "disccount": "TPOS",
    "cpil": "TCMP",
    "albumart": "APIC",
    "encodedby": "TENC",
    "copyright": "TCOP",
    "tempo": "TBPM",
    "lyrics": "USLT::XXX",
    "woas": "WOAS",
    "isrc": "TSRC",
    "explicit": "NULL",
}

TAG_PRESET = {key: key for key in M4A_TAG_PRESET}

TAG_TO_SONG = {
    "title": "name",
    "artist": "artists",
    "album": "album_name",
    "albumartist": "album_artist",
    "genre": "genres",
    "discnumber": "disc_number",
    "year": "year",
    "date": "date",
    "tracknumber": "track_number",
    "encodedby": "publisher",
    "woas": "url",
    "comment": "download_url",
    "isrc": "isrc",
    "copyright": "copyright_text",
    "lyrics": "lyrics",
    "albumart": "album_art",
}

M4A_TO_SONG = {
    value: TAG_TO_SONG.get(key)
    for key, value in M4A_TAG_PRESET.items()
    if TAG_TO_SONG.get(key)
}
MP3_TO_SONG = {
    value: TAG_TO_SONG.get(key)
    for key, value in MP3_TAG_PRESET.items()
    if TAG_TO_SONG.get(key)
}

LRC_REGEX = re.compile(r"(\[\d{2}:\d{2}.\d{2,3}\])")


def embed_metadata(
    output_file: Path,
    song: Song,
    id3_separator: str = "/",
    skip_album_art: Optional[bool] = False,
):
    """
    Set ID3 tags for generic files (FLAC, OPUS, OGG)

    ### Arguments
    - output_file: Path to the output file.
    - song: Song object.
    - id3_separator: The separator used for the id3 tags.
    - skip_album_art: Boolean to skip album art embedding.
    """

    # Get the file extension for the output file
    encoding = output_file.suffix[1:]

    if encoding == "wav":
        embed_wav_file(output_file, song)
        return

    # Get the tag preset for the file extension
    tag_preset = TAG_PRESET if encoding != "m4a" else M4A_TAG_PRESET

    try:
        audio_file = File(str(output_file.resolve()), easy=encoding == "mp3")

        if audio_file is None:
            raise MetadataError(
                f"Unrecognized file format for {output_file} from {song.url}"
            )
    except Exception as exc:
        raise MetadataError("Unable to load file.") from exc

    # Embed basic metadata
    audio_file[tag_preset["artist"]] = song.artists
    audio_file[tag_preset["albumartist"]] = (
        song.album_artist if song.album_artist else song.artist
    )
    audio_file[tag_preset["title"]] = song.name
    audio_file[tag_preset["date"]] = song.date
    audio_file[tag_preset["encodedby"]] = song.publisher

    # Embed metadata that isn't always present
    album_name = song.album_name
    if album_name:
        audio_file[tag_preset["album"]] = album_name

    if song.genres:
        audio_file[tag_preset["genre"]] = song.genres[0].title()

    if song.copyright_text:
        audio_file[tag_preset["copyright"]] = song.copyright_text

    if song.download_url and encoding != "mp3":
        audio_file[tag_preset["comment"]] = song.download_url

    # Embed some metadata in format specific ways
    if encoding in ["flac", "ogg", "opus"]:
        audio_file["discnumber"] = str(song.disc_number)
        audio_file["disctotal"] = str(song.disc_count)
        audio_file["tracktotal"] = str(song.tracks_count)
        audio_file["tracknumber"] = str(song.track_number)
        audio_file["woas"] = song.url
        audio_file["isrc"] = song.isrc
    elif encoding == "m4a":
        audio_file[tag_preset["discnumber"]] = [(song.disc_number, song.disc_count)]
        audio_file[tag_preset["tracknumber"]] = [(song.track_number, song.tracks_count)]
        audio_file[tag_preset["explicit"]] = (4 if song.explicit is True else 2,)
        audio_file[tag_preset["woas"]] = song.url.encode("utf-8")
    elif encoding == "mp3":
        audio_file["tracknumber"] = f"{str(song.track_number)}/{str(song.tracks_count)}"
        audio_file["discnumber"] = f"{str(song.disc_number)}/{str(song.disc_count)}"
        audio_file["isrc"] = song.isrc

    # Mp3 specific encoding
    if encoding == "mp3":
        if id3_separator != "/":
            audio_file.save(v23_sep=id3_separator, v2_version=3)
        else:
            audio_file.save(v2_version=3)

        audio_file = ID3(str(output_file.resolve()))

        audio_file.add(WOAS(encoding=3, url=song.url))

        if song.download_url:
            audio_file.add(COMM(encoding=3, text=song.download_url))

        if song.popularity:
            audio_file.add(
                POPM(
                    rating=int(song.popularity * 255 / 100),
                )
            )

        if song.year:
            audio_file.add(TYER(encoding=3, text=str(song.year)))

    if not skip_album_art:
        # Embed album art
        audio_file = embed_cover(audio_file, song, encoding)

    # Embed lyrics
    audio_file = embed_lyrics(audio_file, song, encoding)

    # Mp3 specific encoding
    if encoding == "mp3":
        audio_file.save(v23_sep=id3_separator, v2_version=3)
    else:
        audio_file.save()


def embed_cover(audio_file, song: Song, encoding: str):
    """
    Embed the album art in the audio file.

    ### Arguments
    - audio_file: Audio file object.
    - song: Song object.
    """

    if not song.cover_url:
        return audio_file

    # Try to download the cover art
    try:
        cover_data = requests.get(
            song.cover_url,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        ).content
    except Exception:
        return audio_file

    # Create the image object for the file type
    if encoding in ["flac", "ogg", "opus"]:
        picture = Picture()
        picture.type = 3
        picture.desc = "Cover"
        picture.mime = "image/jpeg"
        picture.data = cover_data

        if encoding in ["ogg", "opus"]:
            image_data = picture.write()
            encoded_data = base64.b64encode(image_data)
            vcomment_value = encoded_data.decode("ascii")
            if "metadata_block_picture" in audio_file.keys():
                audio_file.pop("metadata_block_picture")
            audio_file["metadata_block_picture"] = [vcomment_value]
        elif encoding == "flac":
            if audio_file.pictures:
                audio_file.clear_pictures()
            audio_file.add_picture(picture)
    elif encoding == "m4a":
        if M4A_TAG_PRESET["albumart"] in audio_file.keys():
            audio_file.pop(M4A_TAG_PRESET["albumart"])
        audio_file[M4A_TAG_PRESET["albumart"]] = [
            MP4Cover(
                cover_data,
                imageformat=MP4Cover.FORMAT_JPEG,
            )
        ]
    elif encoding == "mp3":
        if "APIC:Cover" in audio_file.keys():
            audio_file.pop("APIC:Cover")
        audio_file["APIC"] = APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=cover_data,
        )

    return audio_file


def embed_lyrics(audio_file, song: Song, encoding: str):
    """
    Detect lyrics type (lrc or txt) and embed them in the audio file.

    ### Arguments
    - audio_file: Audio file object.
    - song: Song object.
    - encoding: Encoding type.
    """

    lyrics = song.lyrics
    if not lyrics:
        return audio_file

    tag_preset = TAG_PRESET if encoding != "m4a" else M4A_TAG_PRESET

    # Check if the lyrics are in lrc format
    # using regex on the first 5 lines
    lrc_lines = lyrics.splitlines()[:5]
    lrc_lines = [line for line in lrc_lines if line and LRC_REGEX.match(line)]

    if len(lrc_lines) == 0:
        # Lyrics are not in lrc format
        # Embed them normally
        if encoding == "mp3":
            audio_file.add(USLT(encoding=Encoding.UTF8, text=song.lyrics))
        else:
            audio_file[tag_preset["lyrics"]] = song.lyrics
    else:
        # Lyrics are in lrc format
        # Embed them as SYLT id3 tag
        clean_lyrics = remomve_lrc(lyrics)
        if encoding == "mp3":
            lrc_data = []
            for line in lyrics.splitlines():
                time_tag = line.split("]", 1)[0] + "]"
                text = line.replace(time_tag, "")

                time_tag = time_tag.replace("[", "")
                time_tag = time_tag.replace("]", "")
                time_tag = time_tag.replace(".", ":")
                time_tag_vals = time_tag.split(":")
                if len(time_tag_vals) != 3 or any(
                    not isinstance(tag, int) for tag in time_tag_vals
                ):
                    continue

                minute, sec, millisecond = time_tag_vals
                time = to_ms(min=minute, sec=sec, ms=millisecond)
                lrc_data.append((text, time))

            audio_file.add(USLT(encoding=3, text=clean_lyrics))
            audio_file.add(SYLT(encoding=3, text=lrc_data, format=2, type=1))
        else:
            audio_file[tag_preset["lyrics"]] = song.lyrics

    return audio_file


def get_file_metadata(path: Path, id3_separator: str = "/") -> Optional[Dict[str, Any]]:
    """
    Get song metadata.

    ### Arguments
    - path: Path to the song.

    ### Returns
    - Dict of song metadata.

    ### Raises
    - OSError: If the file is not found.
    - MetadataError: If the file is not a valid audio file.
    """

    if path.exists() is False:
        raise OSError(f"File not found: {path}")

    audio_file = File(str(path.resolve()))

    if audio_file is None or audio_file == {}:
        return None

    song_meta: Dict[str, Any] = {}
    for key in TAG_PRESET:
        if path.suffix == ".m4a":
            val = audio_file.get(M4A_TAG_PRESET[key])
        elif path.suffix == ".mp3":
            val = audio_file.get(MP3_TAG_PRESET[key])
        else:
            val = audio_file.get(key)

        # Cover art is a special case and
        # has to be handled before checking the val
        # M4A is handled in the m4a section since it
        # has data in the val variable
        if key == "albumart":
            if path.suffix == ".mp3":
                cover = audio_file.get("APIC:Cover")
                if cover:
                    song_meta["album_art"] = cover.data
                else:
                    song_meta["album_art"] = None

                continue

            if path.suffix == ".flac":
                song_meta["album_art"] = audio_file.pictures[0].data
                continue

            if path.suffix in [".ogg", ".opus"]:
                pictures = audio_file.get("metadata_block_picture")
                if pictures and pictures[0]:
                    song_meta["album_art"] = pictures[0]
                else:
                    song_meta["album_art"] = None

                continue

        # If the tag is empty, skip it
        if val is None:
            # If the tag is empty but it's key is in the
            # song object, set it to None
            empty_key = TAG_TO_SONG.get(key)
            if empty_key:
                song_meta[empty_key] = None

            continue

        # MP3 specific decoding
        if path.suffix == ".mp3":
            if key == "woas":
                song_meta["url"] = val.url
            elif key == "comment":
                song_meta["download_url"] = val.text[0]
            elif key == "year":
                song_meta["year"] = int(str(val.text[0])[:4])
            elif key == "date":
                song_meta["date"] = str(val.text[0])
            elif key in ["tracknumber", "trackcount"]:
                count = val.text[0].split(id3_separator)
                if len(count) == 2:
                    song_meta["track_number"] = int(count[0])
                    song_meta["tracks_count"] = int(count[1])
                else:
                    song_meta["track_number"] = val.text[0]
            elif key in ["discnumber", "disccount"]:
                count = val.text[0].split(id3_separator)
                if len(count) == 2:
                    song_meta["disc_number"] = int(count[0])
                    song_meta["disc_count"] = int(count[1])
                else:
                    song_meta["disc_number"] = val.text[0]
            elif key == "artist":
                artists_val: str = (
                    val.text[0] if isinstance(val.text, list) else val.text
                )
                song_meta["artists"] = artists_val.split(id3_separator)
            else:
                meta_key = TAG_TO_SONG.get(key)
                if meta_key and song_meta.get(meta_key) is None:
                    song_meta[meta_key] = (
                        val.text[0]
                        if isinstance(val.text, list) and len(val.text) == 1
                        else val.text
                    )

        # M4A specific decoding
        elif path.suffix == ".m4a":
            if key == "artist":
                song_meta["artists"] = val
            elif key == "woas":
                song_meta["url"] = val[0].decode("utf-8")
            elif key == "explicit":
                song_meta["explicit"] = val == [4] if val else None
            elif key == "year":
                song_meta["year"] = int(str(val[0])[:4])
            elif key == "discnumber":
                song_meta["disc_number"] = val[0][0]
                song_meta["disc_count"] = val[0][1]
            elif key == "tracknumber":
                song_meta["track_number"] = val[0][0]
                song_meta["tracks_count"] = val[0][1]
            else:
                meta_key = TAG_TO_SONG.get(key)
                if meta_key:
                    song_meta[meta_key] = (
                        val[0] if isinstance(val, list) and len(val) == 1 else val
                    )

        # FLAC, OGG, OPUS specific decoding
        else:
            if key == "artist":
                song_meta["artists"] = val
            elif key == "tracknumber":
                song_meta["track_number"] = int(val[0])
            elif key == "discnumber":
                song_meta["disc_count"] = int(val[0])
                song_meta["disc_number"] = int(val[0])
            else:
                meta_key = TAG_TO_SONG.get(key)
                if meta_key:
                    song_meta[meta_key] = (
                        val[0] if isinstance(val, list) and len(val) == 1 else val
                    )

    # Make sure that artists is a list
    if isinstance(song_meta["artists"], str):
        song_meta["artists"] = [song_meta["artists"]]
    elif song_meta["artists"] is not None:
        song_meta["artists"] = list(song_meta["artists"])
    else:
        song_meta["artists"] = []

    # Make sure that genres is a list
    if isinstance(song_meta["genres"], str):
        song_meta["genres"] = [song_meta["genres"]]

    # Add main artist to the song meta object
    if song_meta["artists"]:
        song_meta["artist"] = song_meta["artists"][0]
    else:
        song_meta["artist"] = None

    return song_meta


def embed_wav_file(output_file: Path, song: Song):
    """
    Embeds the song metadata into the wav file

    ### Arguments
    - output_file: The output file path
    - song: The song object
    - id3_separator: The separator used for the id3 tags
    """
    audio = WAVE(output_file)
    if audio is None:
        raise ValueError("Invalid audio file")

    if audio.tags:
        audio.tags.clear()

    audio.add_tags()

    audio.tags.add(TIT2(encoding=3, text=song.name))  # type: ignore
    audio.tags.add(TPE1(encoding=3, text=song.artists))  # type: ignore
    audio.tags.add(TALB(encoding=3, text=song.album_name))  # type: ignore
    audio.tags.add(TCOM(encoding=3, text=song.publisher))  # type: ignore
    audio.tags.add(TCON(encoding=3, text=song.genres))  # type: ignore
    audio.tags.add(TDRC(encoding=3, text=song.date))  # type: ignore
    audio.tags.add(  # type: ignore
        TRCK(encoding=3, text=f"{song.track_number}/{song.tracks_count}")  # type: ignore
    )
    audio.tags.add(TDRC(encoding=3, text=song.date))  # type: ignore
    audio.tags.add(WOAS(encoding=3, text=song.url))  # type: ignore
    audio.tags.add(TSRC(encoding=3, text=song.isrc))  # type: ignore

    if song.download_url:
        audio.tags.add(COMM(encoding=3, text=song.download_url))  # type: ignore

    if song.copyright_text:
        audio.tags.add(TCOP(encoding=3, text=song.copyright_text))  # type: ignore

    if song.popularity:
        audio.tags.add(  # type: ignore
            COMM(
                encoding=3,
                lang="eng",
                text="Spotify Popularity: " + str(song.popularity),
            )
        )

    if song.cover_url:
        try:
            cover_data = requests.get(song.cover_url, timeout=10).content
            audio.tags.add(  # type: ignore
                APIC(
                    encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data
                )
            )
        except Exception:
            pass

    if song.lyrics:
        # Check if the lyrics are in lrc format
        # using regex on the first 5 lines
        lrc_lines = song.lyrics.splitlines()[:5]
        lrc_lines = [line for line in lrc_lines if line and LRC_REGEX.match(line)]

        if len(lrc_lines) == 0:
            audio.tags.add(USLT(encoding=Encoding.UTF8, text=song.lyrics))  # type: ignore
        else:
            lrc_data = []
            clean_lyrics = remomve_lrc(song.lyrics)
            for line in song.lyrics.splitlines():
                time_tag = line.split("]", 1)[0] + "]"
                text = line.replace(time_tag, "")

                time_tag = time_tag.replace("[", "")
                time_tag = time_tag.replace("]", "")
                time_tag = time_tag.replace(".", ":")
                time_tag_vals = time_tag.split(":")
                if len(time_tag_vals) != 3 or any(
                    not isinstance(tag, int) for tag in time_tag_vals
                ):
                    continue

                minute, sec, millisecond = time_tag_vals
                time = to_ms(min=minute, sec=sec, ms=millisecond)
                lrc_data.append((text, time))

            audio.tags.add(USLT(encoding=3, text=clean_lyrics))  # type: ignore
            audio.tags.add(SYLT(encoding=3, text=lrc_data, format=2, type=1))  # type: ignore

    audio.save()
