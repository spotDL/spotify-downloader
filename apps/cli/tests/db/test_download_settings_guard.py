"""Seam 1 guard: the eleven Plan-7 download-knob ``Settings`` fields must exist.

The download command routes engine/session knobs (``--restrict``, ``--scan``,
``--add-unavailable``, …) to the embedded server's ``SPOTDL_*`` ``Settings``.
Those fields are a Plan 7 seam this plan **consumes** — if any is missing, the
fix belongs upstream in ``apps/server`` (a Plan 7 follow-up), never a patch here.
"""

from __future__ import annotations

import pytest
from spotdl_server.settings import Settings

_SEAM_FIELDS = [
    "download_restrict",
    "download_max_filename_length",
    "download_id3_separator",
    "download_detect_formats",
    "download_skip_explicit",
    "download_respect_skip_file",
    "download_create_skip_file",
    "download_playlist_numbering",
    "download_retain_track_cover",
    "download_add_unavailable",
    "download_scan_existing",
]


@pytest.mark.parametrize("field", _SEAM_FIELDS)
def test_plan7_download_knob_exists(field: str) -> None:
    if field not in Settings.model_fields:
        pytest.fail(f"Plan 7 seam missing — fix upstream, do not patch apps/server here: {field}")


def test_exactly_eleven_seam_fields() -> None:
    assert len(_SEAM_FIELDS) == 11
    for field in _SEAM_FIELDS:
        assert field in Settings.model_fields
