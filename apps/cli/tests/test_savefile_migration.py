"""``.spotdl`` v4→v2 auto-migration + ``infer_audio_provider`` (CONTRACT G)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from spotdl_cli.errors import ApiError
from spotdl_cli.savefile import dump_save_file, infer_audio_provider, load_save_file

FIXTURE = Path(__file__).parent / "fixtures" / "v4_playlist.spotdl"


def test_v4_fixture_migrates_every_field() -> None:
    save = load_save_file(FIXTURE)

    assert save.version == 2
    assert save.kind == "playlist"  # both songs carry list_name
    assert save.name == "Daft Picks"
    assert save.source is None
    assert save.matcher_version is None
    assert len(save.songs) == 2

    one = save.songs[0]
    assert one.name == "One More Time"
    assert one.artists == ["Daft Punk"]
    assert one.artist == "Daft Punk"
    assert one.album_name == "Discovery"
    assert one.duration_ms == 320357  # 320.357 s → ms (round)
    assert one.isrc == "GBDUW0000059"
    assert one.explicit is False
    assert one.track_number == 1
    assert one.track_count == 14
    assert one.year == 2001
    assert one.date == "2001-03-12"
    assert one.genres == ["french house", "electronic"]
    assert one.publisher == "Virgin"
    assert one.copyright_text == "2001 Virgin Records"
    assert one.popularity == 78
    assert one.cover_url == "https://i.scdn.co/image/cover.jpg"
    assert one.track_url == "https://open.spotify.com/track/0DiWol3AO6WpXZgp0goxAV"
    assert one.provider is None  # v4 didn't record the metadata provider distinctly
    assert one.list_name == "Daft Picks"
    assert one.list_position == 1
    assert one.list_length == 2

    # download_url → match.url; song_id → match.provider_id; provider inferred.
    assert one.match is not None
    assert one.match.url == "https://music.youtube.com/watch?v=fzQ6gRAEoy0"
    assert one.match.provider == "youtube-music"
    assert one.match.provider_id == "0DiWol3AO6WpXZgp0goxAV"
    assert one.match.verified is False

    # A synthesized download block (v4 recorded no per-song download result).
    assert one.download.status == "queued"
    assert one.download.bitrate == "auto"
    assert one.download.output_template == "{artists} - {title}.{output-ext}"


def test_duration_seconds_to_ms() -> None:
    save = load_save_file(FIXTURE)
    assert save.songs[1].duration_ms == 301600  # 301.6 s → ms


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://music.youtube.com/watch?v=x", "youtube-music"),
        ("https://www.youtube.com/watch?v=x", "youtube"),
        ("https://youtu.be/x", "youtube"),
        ("https://soundcloud.com/artist/track", "soundcloud"),
        ("https://x.bandcamp.com/track/y", "bandcamp"),
        ("https://example.org/whatever", "youtube"),  # unknown host → pinned fallback
        ("not a url at all", "youtube"),
    ],
)
def test_infer_audio_provider(url: str, provider: str) -> None:
    assert infer_audio_provider(url) == provider


def test_unrecognized_host_never_fails_validation(tmp_path: Path) -> None:
    """A song whose ``download_url`` host is unknown migrates (provider = youtube)."""
    v4 = [
        {
            "name": "Mystery",
            "artists": ["Someone"],
            "duration": 100.0,
            "url": "https://open.spotify.com/track/mystery",
            "download_url": "https://totally-unknown-host.example/audio",
        }
    ]
    path = tmp_path / "one.spotdl"
    path.write_text(json.dumps(v4), encoding="utf-8")
    save = load_save_file(path)
    assert save.songs[0].match is not None
    assert save.songs[0].match.provider == "youtube"  # required field, never null


def test_v5_file_parses_unchanged(tmp_path: Path) -> None:
    save = load_save_file(FIXTURE)
    v5_path = tmp_path / "roundtrip.spotdl"
    v5_path.write_text(dump_save_file(save), encoding="utf-8")

    reloaded = load_save_file(v5_path)
    assert reloaded.version == 2
    assert reloaded.kind == "playlist"
    assert [s.name for s in reloaded.songs] == ["One More Time", "Digital Love"]


def test_garbage_file_raises_validation_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.spotdl"
    bad.write_text('{"version": 99, "not": "a save file"}', encoding="utf-8")
    with pytest.raises(ApiError) as excinfo:
        load_save_file(bad)
    assert excinfo.value.code.value == "validation_error"


def test_kind_inference_album_when_shared_album(tmp_path: Path) -> None:
    v4 = [
        {"name": "A", "artists": ["X"], "duration": 10.0, "album_name": "Rec"},
        {"name": "B", "artists": ["X"], "duration": 20.0, "album_name": "Rec"},
    ]
    path = tmp_path / "album.spotdl"
    path.write_text(json.dumps(v4), encoding="utf-8")
    save = load_save_file(path)
    assert save.kind == "album"
    assert save.name == "Rec"


def test_kind_inference_single_when_no_context(tmp_path: Path) -> None:
    v4 = [{"name": "Solo", "artists": ["X"], "duration": 10.0}]
    path = tmp_path / "single.spotdl"
    path.write_text(json.dumps(v4), encoding="utf-8")
    save = load_save_file(path)
    assert save.kind == "single"
