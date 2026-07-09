"""Output-path planning for the download pipeline: template rendering (all
VARS), restrict modes, OS filename-length handling, and the PURE
skip/overwrite/archive decision helpers plus archive load/save.

Behaviour is a faithful port of v4 ``spotdl/utils/formatter.py``
(``VARS``/``format_query``/``create_file_name``/``sanitize_string``/
``restrict_filename``/``smart_split``/``create_path_object``) and the
skip/overwrite/archive branches of ``spotdl/download/downloader.py``, rewritten
against the v5 domain model.

The template-variable table is a CONTRACT (Plan 4 Task 4): every ``{var}`` must
render from its documented source. ``render_template`` / ``build_output_path`` /
``smart_split`` / ``restrict_filename`` are pure (no I/O). ``find_duplicates`` /
``plan_skip`` / ``load_archive`` / ``save_archive`` touch the filesystem only via
``Path.exists()`` / read / write.

The v4 ``slugify`` (with pykakasi Japanese handling), used by short-mode
artist-dedup, is imported from Plan 3's ``core.matching.text`` so slugify
semantics stay single-sourced.
"""

from __future__ import annotations

import re
from pathlib import Path
from unicodedata import normalize

from yt_dlp.utils import sanitize_filename  # type: ignore[import-untyped]

from spotdl_core.download.context import (
    DownloadConfig,
    DownloadRequest,
    OverwriteMode,
    RestrictMode,
    SkipReason,
)
from spotdl_core.matching.text import slugify
from spotdl_core.model import Track

# The 20 documented template tokens (CONTRACT). Order matters for substitution:
# ``{artists}`` MUST precede ``{artist}`` (which is a substring) so the plural
# form is replaced first. Mirrors v4 ``VARS`` / ``format_query`` ordering.
VARS: tuple[str, ...] = (
    "{title}",
    "{artists}",
    "{artist}",
    "{album}",
    "{album-artist}",
    "{genre}",
    "{disc-number}",
    "{disc-count}",
    "{duration}",
    "{year}",
    "{original-date}",
    "{track-number}",
    "{tracks-count}",
    "{isrc}",
    "{track-id}",
    "{publisher}",
    "{list-length}",
    "{list-position}",
    "{list-name}",
    "{output-ext}",
)

_DEFAULT_TEMPLATE = "{artists} - {title}.{output-ext}"
_SHORT_TEMPLATE = "{artist} - {title}.{output-ext}"

# Matches text segments that live *outside* ``{...}`` template tokens (v4
# ``create_file_name`` non-template-char measurement).
_NON_TEMPLATE_RE = re.compile(r"(?<!{)[^{}]+(?![^{}]*})")


# --- sanitization ---------------------------------------------------------


def sanitize_string(string: str) -> str:
    """Strip filesystem-hostile characters (port of v4 ``sanitize_string``).

    Removes the Windows-disallowed set ``/?\\*|<>``; maps ``"`` -> ``'`` and
    ``:`` -> ``-`` (retaining a readable equivalent rather than dropping them).
    """
    output = "".join(char for char in string if char not in "/?\\*|<>")
    return output.replace('"', "'").replace(":", "-")


def create_path_object(string: str) -> Path:
    """Build a ``Path`` from a rendered template, trimming leading/trailing
    ``.`` / ``*`` from each path part (port of v4 ``create_path_object``).

    The ``.spotdl`` cache dir is left untouched.
    """
    file = Path(string)
    sanitized_parts: list[str] = []
    for part in file.parts:
        match = re.search(r"[^\.*](.*)[^\.*$]", part)
        if match and part != ".spotdl":
            sanitized_parts.append(match.group(0))
        else:
            sanitized_parts.append(part)
    return Path(*sanitized_parts)


# --- template rendering ---------------------------------------------------


def _var_values(
    track: Track, request: DownloadRequest, *, output_ext: str | None, short: bool
) -> dict[str, object]:
    """Compute the raw (unsanitized) value for every template token."""
    album = track.album

    # Short mode drops artists whose slug already appears in the (slugified)
    # title, then re-inserts the main artist (v4 ``format_query`` short branch).
    if short:
        artists = [a for a in track.artists if slugify(a) not in slugify(track.name)]
        if not artists or artists[0] != track.main_artist:
            artists.insert(0, track.main_artist)
    else:
        artists = list(track.artists)

    track_number = f"{int(track.track_number):02d}" if track.track_number else ""

    list_position = str(request.list_position).zfill(len(str(request.list_length)))

    # Order MUST match ``VARS`` (``{artists}`` before ``{artist}``).
    return {
        "{title}": track.name,
        "{artists}": ", ".join(artists),
        "{artist}": track.main_artist,
        "{album}": album.name if album else "",
        "{album-artist}": (album.album_artist if album else "") or "",
        "{genre}": track.genres[0] if track.genres else "",
        "{disc-number}": track.disc_number,
        "{disc-count}": album.disc_count if album else "",
        "{duration}": round(track.duration_ms / 1000),
        "{year}": track.year,
        "{original-date}": track.date,
        "{track-number}": track_number,
        "{tracks-count}": album.track_count if album else "",
        "{isrc}": track.isrc,
        "{track-id}": track.provider_id,
        "{publisher}": track.publisher,
        "{list-length}": request.list_length,
        "{list-position}": list_position,
        "{list-name}": request.list_name,
        "{output-ext}": output_ext,
    }


def render_template(
    track: Track,
    request: DownloadRequest,
    template: str,
    *,
    output_ext: str | None,
    short: bool = False,
) -> str:
    """Substitute every template token from its documented source (CONTRACT).

    Port of v4 ``format_query`` (always sanitizing): each value is passed through
    :func:`sanitize_string`; ``None`` values render as the empty string. Raises
    ``ValueError`` if the template needs ``{output-ext}`` but none is supplied.
    ``None``-valued ``{list-*}`` tokens are removed and any resulting ``//`` is
    collapsed to ``/``.
    """
    if "{output-ext}" in template and output_ext is None:
        raise ValueError("output_ext is None, but template contains {output-ext}")

    # Drop None-valued list-context tokens and collapse the resulting `//`.
    for key, value in (
        ("{list-length}", request.list_length),
        ("{list-position}", request.list_position),
        ("{list-name}", request.list_name),
    ):
        if key in template and value is None:
            template = template.replace(key, "").replace("//", "/")

    # A template consisting solely of the extension defaults to the full name.
    if template in ("/.{output-ext}", ".{output-ext}"):
        template = _DEFAULT_TEMPLATE

    for key, raw in _var_values(track, request, output_ext=output_ext, short=short).items():
        if key not in template:
            continue
        value = "" if raw is None else sanitize_string(str(raw))
        template = template.replace(key, value)

    return template


# --- restrict modes -------------------------------------------------------


def restrict_filename(path: Path, mode: RestrictMode) -> Path:
    """Restrict the *name* part of ``path`` per ``mode`` (port of v4
    ``restrict_filename``).

    - ``STRICT``: yt-dlp strict filename sanitization, then ``_-_`` -> ``-``.
    - ``ASCII``: NFKD normalize and drop non-ASCII.
    - ``NONE``: unchanged (upstream sanitization already applied).

    An empty result collapses to ``_``.
    """
    if mode is RestrictMode.NONE:
        return path

    if mode is RestrictMode.STRICT:
        result = sanitize_filename(path.name, True, False).replace("_-_", "-")
    else:  # RestrictMode.ASCII
        result = normalize("NFKD", path.name).encode("ascii", "ignore").decode("utf-8")

    return path.with_name(result or "_")


# --- length handling ------------------------------------------------------


def smart_split(string: str, max_length: int, separators: list[str] | None = None) -> str:
    """Return the longest prefix of ``string`` no longer than ``max_length``,
    broken at the first separator that yields a fitting result (port of v4
    ``smart_split``). Hard-truncates when no separator fits.

    Default separators (widest to narrowest): ``["-", ",", " ", ""]`` — the
    empty separator splits on whitespace.
    """
    if separators is None:
        separators = ["-", ",", " ", ""]

    for separator in separators:
        parts = string.split(separator if separator != "" else None)
        new_string = separator.join(parts[:1])
        for part in parts[1:]:
            if len(new_string) + len(separator) + len(part) > max_length:
                break
            new_string += separator + part

        if len(new_string) <= max_length:
            return new_string

    return string[:max_length]


def _normalize_template(template: str) -> str:
    """Apply v4 ``create_file_name`` template-normalization rules."""
    if not any(key in template for key in VARS) and template != "":
        template += "/" + _DEFAULT_TEMPLATE
    if template == "":
        template = _DEFAULT_TEMPLATE
    if template.endswith("/") or template.endswith("\\"):
        template += "/" + _DEFAULT_TEMPLATE
    if not template.endswith(".{output-ext}"):
        template += ".{output-ext}"
    return template


def _render_file_name(
    track: Track,
    request: DownloadRequest,
    template: str,
    output_ext: str,
    restrict: RestrictMode,
    short: bool,
    file_name_length: int | None,
) -> Path:
    """Recursive port of v4 ``create_file_name`` returning a *relative* path."""
    template = _normalize_template(template)

    file = create_path_object(
        render_template(track, request, template, output_ext=output_ext, short=short)
    )

    length_limit = file_name_length or 255

    if len(file.name) < length_limit:
        return restrict_filename(file, restrict)

    # First fallback: retry in short mode (drops in-title artists, main only).
    if not short:
        return _render_file_name(track, request, template, output_ext, restrict, True, length_limit)

    # Second fallback: shorten the artist/title values via smart_split.
    non_template_chars = _NON_TEMPLATE_RE.findall(template)
    half_length = int((length_limit * 0.50) - (len("".join(non_template_chars)) / 2))

    is_long_artist = len(track.main_artist) > half_length
    is_long_title = len(track.name) > half_length

    path_separator = "/" if "/" in template else "\\"
    name_template_parts = template.rsplit(path_separator, 1)
    name_template = name_template_parts[-1]

    new_track = track
    if is_long_artist:
        new_track = new_track.model_copy(
            update={"artists": (smart_split(track.main_artist, half_length),)}
        )
    if is_long_title:
        new_track = new_track.model_copy(update={"name": smart_split(track.name, half_length)})

    new_file = create_path_object(
        render_template(new_track, request, name_template, output_ext=output_ext, short=short)
    )

    if len(new_file.name) > length_limit:
        # Third fallback: the minimal default template, shortened.
        if template == _SHORT_TEMPLATE:
            raise ValueError(
                "File name is still too long, but the template is already "
                "minimal. Try a different template or a larger "
                "max_filename_length."
            )
        return _render_file_name(
            new_track, request, _SHORT_TEMPLATE, output_ext, restrict, True, length_limit
        )

    return new_file


def build_output_path(
    request: DownloadRequest, config: DownloadConfig, *, short: bool = False
) -> Path:
    """Resolve the absolute output ``Path`` for ``request`` under
    ``config.output_dir`` (port of v4 ``create_file_name`` + output-dir join).

    Normalizes the template (default/append rules), renders and sanitizes it,
    enforces ``max_filename_length`` (short mode -> smart_split -> minimal
    template), and applies the restrict mode. An absolute rendered template
    overrides ``config.output_dir``.
    """
    relative = _render_file_name(
        track=request.track,
        request=request,
        template=request.output_template,
        output_ext=request.output_format.value,
        restrict=request.restrict,
        short=short,
        file_name_length=request.max_filename_length,
    )
    return config.output_dir / relative


# --- duplicate / skip decisions (filesystem-reading, no writes) -----------


def find_duplicates(
    output_path: Path,
    known_paths: tuple[Path, ...],
    detect_formats: tuple[object, ...],
) -> list[Path]:
    """Return existing files that duplicate ``output_path`` (port of v4's
    duplicate scan).

    Includes ``known_paths`` (from a prior metadata scan) and, for every format
    in ``detect_formats``, the same stem with that extension. The exact
    ``output_path`` and non-existent files are excluded. ``detect_formats``
    holds ``OutputFormat`` members (only ``.value`` is used).
    """
    output_abs = output_path.absolute()
    duplicates: list[Path] = []

    for path in known_paths:
        if path.absolute() != output_abs and path.exists() and path not in duplicates:
            duplicates.append(path)

    for fmt in detect_formats:
        ext_path = output_path.with_suffix(f".{fmt.value}")  # type: ignore[attr-defined]
        if ext_path.absolute() != output_abs and ext_path.exists() and ext_path not in duplicates:
            duplicates.append(ext_path)

    return duplicates


def plan_skip(
    request: DownloadRequest, output_path: Path, duplicates: list[Path]
) -> SkipReason | None:
    """PURE skip decision: return the first applicable :class:`SkipReason`, or
    ``None`` when the track should be downloaded.

    Reads only existence of ``output_path`` and its ``.skip`` sidecar, plus
    ``request`` inputs (archive membership, explicit flag, overwrite mode). Never
    writes. ``overwrite=METADATA`` and ``overwrite=FORCE`` are NOT skips — the
    engine handles them.
    """
    skip_sidecar = Path(str(output_path.absolute()) + ".skip")
    file_exists = output_path.exists() or bool(duplicates)

    if request.respect_skip_file and skip_sidecar.exists():
        return SkipReason.SKIP_FILE

    if file_exists and request.overwrite is OverwriteMode.SKIP:
        return SkipReason.ALREADY_EXISTS

    if request.track_url is not None and request.track_url in request.archive:
        return SkipReason.IN_ARCHIVE

    if request.track.explicit is True and request.skip_explicit:
        return SkipReason.EXPLICIT_FILTERED

    return None


# --- archive --------------------------------------------------------------


def archive_should_add(outcome_ok: bool, add_unavailable: bool) -> bool:
    """v4 archive-add rule: record a URL when the download succeeded, or always
    when ``add_unavailable`` is set."""
    return outcome_ok or add_unavailable


def load_archive(path: Path) -> frozenset[str]:
    """Read an archive file (one URL per line). Empty set if the file is
    absent; blank lines are ignored."""
    if not path.exists():
        return frozenset()
    with path.open(encoding="utf-8") as handle:
        return frozenset(line.strip() for line in handle if line.strip())


def save_archive(path: Path, urls: frozenset[str]) -> None:
    """Write ``urls`` to ``path``, one sorted URL per line."""
    path.write_text("".join(f"{url}\n" for url in sorted(urls)), encoding="utf-8")
