# -*- coding: utf-8 -*-
"""This module contains a lookup table of YouTube's itag values."""
from typing import Dict

ITAGS = {
    5: ("240p", "64kbps"),
    6: ("270p", "64kbps"),
    13: ("144p", None),
    17: ("144p", "24kbps"),
    18: ("360p", "96kbps"),
    22: ("720p", "192kbps"),
    34: ("360p", "128kbps"),
    35: ("480p", "128kbps"),
    36: ("240p", None),
    37: ("1080p", "192kbps"),
    38: ("3072p", "192kbps"),
    43: ("360p", "128kbps"),
    44: ("480p", "128kbps"),
    45: ("720p", "192kbps"),
    46: ("1080p", "192kbps"),
    59: ("480p", "128kbps"),
    78: ("480p", "128kbps"),
    82: ("360p", "128kbps"),
    83: ("480p", "128kbps"),
    84: ("720p", "192kbps"),
    85: ("1080p", "192kbps"),
    91: ("144p", "48kbps"),
    92: ("240p", "48kbps"),
    93: ("360p", "128kbps"),
    94: ("480p", "128kbps"),
    95: ("720p", "256kbps"),
    96: ("1080p", "256kbps"),
    100: ("360p", "128kbps"),
    101: ("480p", "192kbps"),
    102: ("720p", "192kbps"),
    132: ("240p", "48kbps"),
    151: ("720p", "24kbps"),
    # DASH Video
    133: ("240p", None),
    134: ("360p", None),
    135: ("480p", None),
    136: ("720p", None),
    137: ("1080p", None),
    138: ("2160p", None),
    160: ("144p", None),
    167: ("360p", None),
    168: ("480p", None),
    169: ("720p", None),
    170: ("1080p", None),
    212: ("480p", None),
    218: ("480p", None),
    219: ("480p", None),
    242: ("240p", None),
    243: ("360p", None),
    244: ("480p", None),
    245: ("480p", None),
    246: ("480p", None),
    247: ("720p", None),
    248: ("1080p", None),
    264: ("1440p", None),
    266: ("2160p", None),
    271: ("1440p", None),
    272: ("2160p", None),
    278: ("144p", None),
    298: ("720p", None),
    299: ("1080p", None),
    302: ("720p", None),
    303: ("1080p", None),
    308: ("1440p", None),
    313: ("2160p", None),
    315: ("2160p", None),
    330: ("144p", None),
    331: ("240p", None),
    332: ("360p", None),
    333: ("480p", None),
    334: ("720p", None),
    335: ("1080p", None),
    336: ("1440p", None),
    337: ("2160p", None),
    # DASH Audio
    139: (None, "48kbps"),
    140: (None, "128kbps"),
    141: (None, "256kbps"),
    171: (None, "128kbps"),
    172: (None, "256kbps"),
    249: (None, "50kbps"),
    250: (None, "70kbps"),
    251: (None, "160kbps"),
    256: (None, None),
    258: (None, None),
    325: (None, None),
    328: (None, None),
}

HDR = [330, 331, 332, 333, 334, 335, 336, 337]
_60FPS = [298, 299, 302, 303, 308, 315] + HDR
_3D = [82, 83, 84, 85, 100, 101, 102]
LIVE = [91, 92, 93, 94, 95, 96, 132, 151]
DASH_MP4_VIDEO = [133, 134, 135, 136, 137, 138, 160, 212, 264, 266, 298, 299]
DASH_MP4_AUDIO = [139, 140, 141, 256, 258, 325, 328]
DASH_WEBM_VIDEO = [
    167,
    168,
    169,
    170,
    218,
    219,
    278,
    242,
    243,
    244,
    245,
    246,
    247,
    248,
    271,
    272,
    302,
    303,
    308,
    313,
    315,
]
DASH_WEBM_AUDIO = [171, 172, 249, 250, 251]


def get_format_profile(itag: int) -> Dict:
    """Get additional format information for a given itag.

    :param str itag:
        YouTube format identifier code.
    """
    itag = int(itag)
    if itag in ITAGS:
        res, bitrate = ITAGS[itag]
    else:
        res, bitrate = None, None
    return {
        "resolution": res,
        "abr": bitrate,
        "is_live": itag in LIVE,
        "is_3d": itag in _3D,
        "is_hdr": itag in HDR,
        "fps": 60 if itag in _60FPS else 30,
        "is_dash": itag in DASH_MP4_VIDEO
        or itag in DASH_MP4_AUDIO
        or itag in DASH_WEBM_VIDEO
        or itag in DASH_WEBM_AUDIO,
    }
