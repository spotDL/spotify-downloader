# This code has been taken from PyTube
# https://github.com/nficano/pytube
# and is based on various patches required to keep PyTube usable.

# We need to do this since PyTube isn't being maintained.

# The below code is LICENSED under:
"""
Copyright (c) 2019 Nick Ficano

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sub-license, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice, and every other copyright notice found in this
software, and all the attributions in every file, and this permission notice
shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
# The original LICENSE notice can be found on
# https://github.com/nficano/pytube/blob/master/LICENSE


import pytube
from pytube.extract import get_ytplayer_config, apply_signature

def apply_patches():
    """
    This methods applies all the needed patches on PyTube.
    """
    # Patch 1: https://github.com/nficano/pytube/pull/643
    pytube.__main__.apply_descrambler = apply_descrambler
    # Patch 2: https://github.com/nficano/pytube/pull/634
    pytube.__main__.YouTube.extract_title = extract_title
    pytube.__main__.YouTube.descramble = descramble


# The below imports are required by the patches
import json
from html import unescape
from urllib.parse import parse_qs, parse_qsl, unquote

def apply_descrambler(stream_data, key):
    """Apply various in-place transforms to YouTube's media stream data.
    Creates a ``list`` of dictionaries by string splitting on commas, then
    taking each list item, parsing it as a query string, converting it to a
    ``dict`` and unquoting the value.
    :param dict stream_data:
        Dictionary containing query string encoded values.
    :param str key:
        Name of the key in dictionary.
    **Example**:
    >>> d = {'foo': 'bar=1&var=test,em=5&t=url%20encoded'}
    >>> apply_descrambler(d, 'foo')
    >>> print(d)
    {'foo': [{'bar': '1', 'var': 'test'}, {'em': '5', 't': 'url encoded'}]}
    """
    otf_type = "FORMAT_STREAM_TYPE_OTF"

    if key == "url_encoded_fmt_stream_map" and not stream_data.get(
        "url_encoded_fmt_stream_map"
    ):
        formats = json.loads(stream_data["player_response"])["streamingData"]["formats"]
        formats.extend(
            json.loads(stream_data["player_response"])["streamingData"][
                "adaptiveFormats"
            ]
        )
        try:
            stream_data[key] = [
                {
                    "url": format_item["url"],
                    "type": format_item["mimeType"],
                    "quality": format_item["quality"],
                    "itag": format_item["itag"],
                    "bitrate": format_item.get("bitrate"),
                    "is_otf": (format_item.get("type") == otf_type),
                }
                for format_item in formats
            ]
        except KeyError:
            cipher_url = []
            for data in formats:
                cipher = data.get("cipher") or data["signatureCipher"]
                cipher_url.append(parse_qs(cipher))
            stream_data[key] = [
                {
                    "url": cipher_url[i]["url"][0],
                    "s": cipher_url[i]["s"][0],
                    "type": format_item["mimeType"],
                    "quality": format_item["quality"],
                    "itag": format_item["itag"],
                    "bitrate": format_item.get("bitrate"),
                    "is_otf": (format_item.get("type") == otf_type),
                }
                for i, format_item in enumerate(formats)
            ]
    else:
        stream_data[key] = [
            {k: unquote(v) for k, v in parse_qsl(i)}
            for i in stream_data[key].split(",")
        ]


def extract_title(self):
    html_lower = self.watch_html.lower()
    i_start = html_lower.index('<meta property="og:title" content="') + len(
        '<meta property="og:title" content="'
    )
    curr_i = i_start
    end_found = False
    while not end_found:
        # search for the end of the tag: ">
        if html_lower[curr_i] == '"' and html_lower[curr_i + 1] == ">":
            i_end = curr_i
            end_found = True
        curr_i += 1

    return self.watch_html[i_start:i_end].strip()


def descramble(self) -> None:
    """Descramble the stream data and build Stream instances.
    The initialization process takes advantage of Python's
    "call-by-reference evaluation," which allows dictionary transforms to
    be applied in-place, instead of holding references to mutations at each
    interstitial step.
    :rtype: None
    """
    self.vid_info = dict(parse_qsl(self.vid_info_raw))
    if self.age_restricted:
        self.player_config_args = self.vid_info
    else:
        assert self.watch_html is not None
        self.player_config_args = get_ytplayer_config(self.watch_html)["args"]

        # Fix for KeyError: 'title' issue #434
        if "title" not in self.player_config_args:  # type: ignore
            title = self.extract_title()
            self.player_config_args["title"] = unescape(title)

    # https://github.com/nficano/pytube/issues/165
    stream_maps = ["url_encoded_fmt_stream_map"]
    if "adaptive_fmts" in self.player_config_args:
        stream_maps.append("adaptive_fmts")

    # unscramble the progressive and adaptive stream manifests.
    for fmt in stream_maps:
        if not self.age_restricted and fmt in self.vid_info:
            apply_descrambler(self.vid_info, fmt)
        apply_descrambler(self.player_config_args, fmt)

        if not self.js:
            if not self.embed_html:
                self.embed_html = request.get(url=self.embed_url)
            self.js_url = extract.js_url(self.embed_html)
            self.js = request.get(self.js_url)

        apply_signature(self.player_config_args, fmt, self.js)

        # build instances of :class:`Stream <Stream>`
        self.initialize_stream_objects(fmt)

    # load the player_response object (contains subtitle information)
    self.player_response = json.loads(self.player_config_args["player_response"])
    del self.player_config_args["player_response"]
    self.stream_monostate.title = self.title
    self.stream_monostate.duration = self.length

