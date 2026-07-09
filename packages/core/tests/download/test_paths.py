"""Tests for ``spotdl_core.download.paths`` — templating (all VARS), restrict
modes, length limits, and the pure skip/archive decision helpers.

Behaviour is a faithful port of v4 ``spotdl/utils/formatter.py`` and the
skip/overwrite/archive branches of ``spotdl/download/downloader.py``; the
template-variable table is a CONTRACT (Plan 4 Task 4 brief).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from spotdl_core.download.context import (
    DownloadRequest,
    OutputFormat,
    OverwriteMode,
    RestrictMode,
    SkipReason,
)
from spotdl_core.download.paths import (
    VARS,
    archive_should_add,
    build_output_path,
    find_duplicates,
    load_archive,
    plan_skip,
    render_template,
    restrict_filename,
    save_archive,
    smart_split,
)
from spotdl_core.model import AlbumRef, AudioCandidate, ProviderId, Track

# --- shared fixtures ------------------------------------------------------


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt123",
        url="https://youtube.com/watch?v=yt123",
        name="Song Name",
    )


def _full_track() -> Track:
    return Track(
        name="Song Name",
        artists=("Main Artist", "Second"),
        duration_ms=214_000,
        album=AlbumRef(
            name="Album",
            album_artist="Album Artist",
            year=2020,
            track_count=12,
            disc_count=2,
            cover_url="http://x/c.jpg",
        ),
        isrc="USABC1234567",
        explicit=True,
        track_number=5,
        disc_number=1,
        genres=("Pop", "Rock"),
        year=2020,
        date="2019-05-01",
        publisher="Some Label",
        provider=ProviderId.SPOTIFY,
        provider_id="trackid123",
    )


def _request(track: Track | None = None, **kwargs: object) -> DownloadRequest:
    base: dict[str, object] = {
        "track": track or _full_track(),
        "candidate": _candidate(),
        "output_template": "",
        "list_name": "My List",
        "list_position": 3,
        "list_length": 25,
    }
    base.update(kwargs)
    return DownloadRequest(**base)  # type: ignore[arg-type]


# --- render_template ------------------------------------------------------

ALL_VARS_TEMPLATE = (
    "{title}|{artists}|{artist}|{album}|{album-artist}|{genre}|{disc-number}|"
    "{disc-count}|{duration}|{year}|{original-date}|{track-number}|{tracks-count}|"
    "{isrc}|{track-id}|{publisher}|{list-length}|{list-position}|{list-name}|{output-ext}"
)


def test_render_template_substitutes_every_var() -> None:
    request = _request()
    result = render_template(request.track, request, ALL_VARS_TEMPLATE, output_ext="mp3")
    assert result == (
        "Song Name|Main Artist, Second|Main Artist|Album|Album Artist|Pop|1|"
        "2|214|2020|2019-05-01|05|12|"
        "USABC1234567|trackid123|Some Label|25|03|My List|mp3"
    )


def test_vars_lists_all_twenty_tokens() -> None:
    assert len(VARS) == 20
    for token in ("{title}", "{artists}", "{artist}", "{output-ext}", "{list-name}"):
        assert token in VARS


def test_render_template_missing_album_and_list_render_empty() -> None:
    track = _full_track().model_copy(update={"album": None})
    request = _request(track=track, list_name=None, list_position=None, list_length=None)
    result = render_template(
        track, request, "{album}|{album-artist}|{disc-count}|{tracks-count}", output_ext="mp3"
    )
    assert result == "|||"


def test_render_template_output_ext_required() -> None:
    request = _request()
    with pytest.raises(ValueError):
        render_template(request.track, request, "{title}.{output-ext}", output_ext=None)


def test_render_template_none_list_collapses_double_slash() -> None:
    request = _request(list_name=None)
    # {list-name} None -> removed, and the resulting `//` collapses to `/`.
    result = render_template(request.track, request, "a/{list-name}/{title}", output_ext="mp3")
    assert result == "a/Song Name"


def test_render_template_short_mode_drops_artist_in_title() -> None:
    track = Track(
        name="Main Artist - Song",
        artists=("Main Artist",),
        duration_ms=200_000,
    )
    request = _request(track=track)
    result = render_template(track, request, "{artists}", output_ext="mp3", short=True)
    assert result == "Main Artist"


# --- build_output_path ----------------------------------------------------


def test_build_output_path_empty_template_default(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    request = _request(output_template="")
    path = build_output_path(request, config)
    assert path == tmp_path / "Main Artist, Second - Song Name.mp3"


def test_build_output_path_no_vars_appends_default(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    request = _request(output_template="Music")
    path = build_output_path(request, config)
    assert path == tmp_path / "Music" / "Main Artist, Second - Song Name.mp3"


def test_build_output_path_trailing_slash_appends_default(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    request = _request(output_template="Playlists/{list-name}/")
    path = build_output_path(request, config)
    assert path == tmp_path / "Playlists" / "My List" / "Main Artist, Second - Song Name.mp3"


def test_build_output_path_appends_output_ext(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    request = _request(output_template="{artist} - {title}")
    path = build_output_path(request, config)
    assert path == tmp_path / "Main Artist - Song Name.mp3"


def test_build_output_path_format_extension_used(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    request = _request(output_template="", output_format=OutputFormat.FLAC)
    path = build_output_path(request, config)
    assert path.suffix == ".flac"


# --- restrict -------------------------------------------------------------


def test_restrict_strict() -> None:
    result = restrict_filename(Path("Beyoncé - Déjà Vu.mp3"), RestrictMode.STRICT)
    assert result.name == "Beyonce-Deja_Vu.mp3"


def test_restrict_ascii() -> None:
    result = restrict_filename(Path("Beyoncé - Déjà Vu.mp3"), RestrictMode.ASCII)
    assert result.name == "Beyonce - Deja Vu.mp3"


def test_restrict_empty_becomes_underscore() -> None:
    result = restrict_filename(Path("日本語"), RestrictMode.ASCII)
    assert result.name == "_"


def test_restrict_none_unchanged() -> None:
    result = restrict_filename(Path("Café.mp3"), RestrictMode.NONE)
    assert result.name == "Café.mp3"


def test_build_output_path_applies_restrict(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    track = _full_track().model_copy(update={"name": "Déjà Vu", "artists": ("Beyoncé",)})
    request = _request(
        track=track, output_template="{artist} - {title}", restrict=RestrictMode.STRICT
    )
    path = build_output_path(request, config)
    assert path.name == "Beyonce-Deja_Vu.mp3"


# --- length limits --------------------------------------------------------


def test_build_output_path_length_smart_split(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    track = Track(name="A" * 100, artists=("John",), duration_ms=200_000)
    request = _request(track=track, output_template="", max_filename_length=40)
    path = build_output_path(request, config)
    assert path.name == "John - " + "A" * 18 + ".mp3"
    assert len(path.name) <= 40


def test_build_output_path_length_raises_when_still_too_long(tmp_path: Path) -> None:
    from spotdl_core.download.context import DownloadConfig

    config = DownloadConfig(output_dir=tmp_path, temp_dir=tmp_path / "tmp")
    track = Track(name="B" * 50, artists=("A" * 50,), duration_ms=200_000)
    request = _request(track=track, output_template="", max_filename_length=10)
    with pytest.raises(ValueError):
        build_output_path(request, config)


# --- smart_split ----------------------------------------------------------


def test_smart_split_stops_at_first_fitting_separator() -> None:
    assert smart_split("The Quick Brown Fox", 10) == "The Quick"


def test_smart_split_hard_truncates_when_none_fit() -> None:
    assert smart_split("abcdefghij klmno", 5) == "abcde"


def test_smart_split_custom_separators() -> None:
    assert smart_split("a-b-c-d", 3, ["-"]) == "a-b"


# --- find_duplicates ------------------------------------------------------


def test_find_duplicates_known_paths_and_formats(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    output_path.write_text("x")
    other = tmp_path / "other.mp3"
    other.write_text("x")
    flac = tmp_path / "song.flac"
    flac.write_text("x")
    missing = tmp_path / "missing.mp3"

    dups = find_duplicates(
        output_path,
        known_paths=(other, output_path, missing),
        detect_formats=(OutputFormat.FLAC, OutputFormat.MP3),
    )
    assert other in dups
    assert flac in dups
    assert output_path not in dups  # exact output excluded
    assert missing not in dups  # non-existent excluded


# --- plan_skip ------------------------------------------------------------


def test_plan_skip_skip_file(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    Path(str(output_path.absolute()) + ".skip").write_text("")
    request = _request(respect_skip_file=True)
    assert plan_skip(request, output_path, []) is SkipReason.SKIP_FILE


def test_plan_skip_already_exists(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    output_path.write_text("x")
    request = _request(overwrite=OverwriteMode.SKIP)
    assert plan_skip(request, output_path, []) is SkipReason.ALREADY_EXISTS


def test_plan_skip_in_archive(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    request = _request(
        track_url="https://open.spotify.com/track/abc",
        archive=frozenset({"https://open.spotify.com/track/abc"}),
    )
    assert plan_skip(request, output_path, []) is SkipReason.IN_ARCHIVE


def test_plan_skip_explicit(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    track = _full_track().model_copy(update={"explicit": True})
    request = _request(track=track, skip_explicit=True)
    assert plan_skip(request, output_path, []) is SkipReason.EXPLICIT_FILTERED


def test_plan_skip_none_when_nothing_applies(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    track = _full_track().model_copy(update={"explicit": False})
    request = _request(track=track)
    assert plan_skip(request, output_path, []) is None


def test_plan_skip_force_does_not_skip_existing(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    output_path.write_text("x")
    track = _full_track().model_copy(update={"explicit": False})
    request = _request(track=track, overwrite=OverwriteMode.FORCE)
    assert plan_skip(request, output_path, []) is None


def test_plan_skip_metadata_is_not_a_skip(tmp_path: Path) -> None:
    output_path = tmp_path / "song.mp3"
    output_path.write_text("x")
    track = _full_track().model_copy(update={"explicit": False})
    request = _request(track=track, overwrite=OverwriteMode.METADATA)
    assert plan_skip(request, output_path, []) is None


# --- archive --------------------------------------------------------------


def test_archive_should_add() -> None:
    assert archive_should_add(True, False) is True
    assert archive_should_add(False, True) is True
    assert archive_should_add(False, False) is False


def test_archive_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "archive.txt"
    save_archive(path, frozenset({"b", "a", "c"}))
    assert path.read_text(encoding="utf-8") == "a\nb\nc\n"
    assert load_archive(path) == frozenset({"a", "b", "c"})


def test_load_archive_absent_is_empty(tmp_path: Path) -> None:
    assert load_archive(tmp_path / "nope.txt") == frozenset()


def test_save_archive_empty(tmp_path: Path) -> None:
    path = tmp_path / "archive.txt"
    save_archive(path, frozenset())
    assert path.read_text(encoding="utf-8") == ""
    assert load_archive(path) == frozenset()
