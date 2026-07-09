"""spotDL v4 → v5 command-line compatibility shim (CONTRACT F).

v5 is a ground-up rewrite, but it deliberately keeps v4's operation names
(``download`` / ``save`` / ``sync`` / ``meta`` / ``url`` / ``web``) and most
everyday flag names. That lets the CLI accept a *v4-style* invocation, normalize
it into the v5 form, and hand it to Typer — instead of shipping a second parser.

:func:`translate_v4_argv` is a **pure** function run in ``__main__.main()``
*before* Typer parses. It returns one of three results:

* :class:`Unchanged` — the argv is already valid v5; pass it straight through.
* :class:`Rewritten` — the argv was normalized (renamed flags, stripped no-ops,
  bare-query sugar); ``notices`` are printed to stderr and ``argv`` handed to Typer.
* :class:`Dropped` — the argv used a flag whose behavior v5 no longer performs
  client-side; ``main()`` prints an error and exits ``USAGE`` (2). Drops take
  precedence and fail fast, even when renames/soft-drops are also present.

The heart of the shim is :data:`V4_FLAG_TABLE`, a single module-level data
structure enumerating **every** flag from v4's ``arguments.py``. Each row is one
of four *kinds*:

* **SAME** — the token passes through unchanged.
* **RENAME** — the token is rewritten to its v5 form (and a one-line note is
  printed once for the whole invocation).
* **SOFT-DROP** — the flag is now a meaningless no-op (its v4 behavior is
  automatic in v5): the token (and its value, if any) is stripped, a warning is
  printed, and execution continues.
* **DROP** — the flag named behavior that genuinely moved server-side: the shim
  errors with an actionable pointer to the replacement and exits ``USAGE``.

:data:`V4_FLAG_TABLE` (and the ``.spotdl`` field table :data:`SPOTDL_FIELD_TABLE`)
are also the **single source of truth for the migration guide** (spec §12):
``scripts/docs/gen_migration_guide.py`` imports them and renders
``docs/migration/v4-to-v5.md`` from the same rows the shim enforces, so the docs
can never drift from the shim's actual behavior. The generator reads each flag
row's ``v4_flag`` / ``kind`` / ``v5_form`` attributes and each field row's
``v4_field`` / ``v2_field`` / ``note`` attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# v4 operations that survive verbatim as v5 subcommands (``web`` → ``spotdl web``).
V4_OPERATIONS: frozenset[str] = frozenset({"download", "save", "sync", "meta", "url", "web"})

# The full v5 leading-command surface: the v4 operations above plus the v5-only
# subcommands (which have no v4 equivalent). A bare first positional that names one
# of these *is* the command, so bare-query sugar must never wrap it in ``download``
# (``spotdl config get`` must stay ``config get``, not become ``download config get``).
# Kept in lockstep with the commands registered in ``__main__`` (which imports this
# set to make the same routing decision for a v5-native argv).
V5_COMMANDS: frozenset[str] = V4_OPERATIONS | frozenset(
    {"search", "server", "config", "auth", "ffmpeg", "read", "version", "status", "tui"}
)


@dataclass(frozen=True)
class FlagSpec:
    """One row of :data:`V4_FLAG_TABLE`.

    ``v4_flag`` / ``kind`` / ``v5_form`` are the documented, migration-guide-facing
    columns (consumed by ``scripts/docs/gen_migration_guide.py``). The remaining
    fields drive the runtime translation:

    * ``flags`` — the individual v4 tokens this row covers (a row may group
      several equivalent flags, e.g. the Spotify-credential flags).
    * ``takes_value`` — the flag consumes the following token as a required value
      (so it is skipped, not re-interpreted as another flag / operation).
    * ``rename_to`` — for RENAME rows, the replacement token(s).
    * ``pointer`` — for DROP / SOFT-DROP rows, the runtime pointer copy.
    * ``operation`` — the flag *is* a v4 operation (``--download-ffmpeg`` /
      ``--generate-config``) that becomes a v5 subcommand.
    """

    v4_flag: str
    kind: str
    v5_form: str
    flags: tuple[str, ...]
    takes_value: bool = False
    rename_to: tuple[str, ...] = ()
    pointer: str = ""
    operation: bool = False
    bare_default: str | None = None
    """v4 allowed this flag bare; when the next token is a flag (or end), inject
    this value so the v5 required-value option still parses (v4 parity)."""


@dataclass(frozen=True)
class FieldSpec:
    """One row of :data:`SPOTDL_FIELD_TABLE` (the ``.spotdl`` v4 → v2 field map).

    This mirrors CONTRACT G (whose migration *logic* lives in ``savefile.py``); it
    exists here only as the migration-guide's documentation projection, because
    ``gen_migration_guide.py`` imports both tables from ``spotdl_cli.shim``.
    """

    v4_field: str
    v2_field: str
    note: str


# ---------------------------------------------------------------------------
# The translation table — every flag in v4's ``arguments.py``. Row order is
# grouped for the rendered guide (the generator further groups by kind). The
# ``v5_form`` cells are the documentation column; ``pointer`` is the terminal copy.
# ---------------------------------------------------------------------------
_RETAIN_TRACK_COVER_FORM = (
    "`--retain-track-cover` — **documented behavior gap:** v4's flag *also* set "
    "each track's album name to the playlist name; v5's `--retain-track-cover` "
    "only retains per-track cover art. To get the album-name override too, "
    "combine with `--playlist-numbering`. The rendered migration guide carries "
    "this note verbatim."
)

V4_FLAG_TABLE: tuple[FlagSpec, ...] = (
    # --- SAME: identical name and meaning -----------------------------------
    FlagSpec(
        "--output",
        "SAME",
        "`--output` (output template incl. dir)",
        ("--output",),
        takes_value=True,
    ),
    FlagSpec("--format", "SAME", "`--format`", ("--format",), takes_value=True),
    FlagSpec("--bitrate", "SAME", "`--bitrate`", ("--bitrate",), takes_value=True),
    FlagSpec("--overwrite", "SAME", "`--overwrite`", ("--overwrite",), takes_value=True),
    FlagSpec(
        "--restrict",
        "SAME",
        "`--restrict` (`--restrict` with no value → `--restrict strict`)",
        ("--restrict",),
        takes_value=True,
        bare_default="strict",
    ),
    FlagSpec(
        "--m3u",
        "SAME",
        "`--m3u` (optional value; default `{list[0]}.m3u8`)",
        ("--m3u",),
        takes_value=True,
        bare_default="{list[0]}.m3u8",
    ),
    FlagSpec("--save-file", "SAME", "`--save-file`", ("--save-file",), takes_value=True),
    FlagSpec("--archive", "SAME", "`--archive`", ("--archive",), takes_value=True),
    FlagSpec("--cookie-file", "SAME", "`--cookie-file`", ("--cookie-file",), takes_value=True),
    FlagSpec("--proxy", "SAME", "`--proxy`", ("--proxy",), takes_value=True),
    FlagSpec(
        "--threads", "SAME", "`--threads` (download concurrency)", ("--threads",), takes_value=True
    ),
    FlagSpec("--ffmpeg", "SAME", "`--ffmpeg` (executable path)", ("--ffmpeg",), takes_value=True),
    FlagSpec("--ffmpeg-args", "SAME", "`--ffmpeg-args`", ("--ffmpeg-args",), takes_value=True),
    FlagSpec("--yt-dlp-args", "SAME", "`--yt-dlp-args`", ("--yt-dlp-args",), takes_value=True),
    FlagSpec("--sponsor-block", "SAME", "`--sponsor-block`", ("--sponsor-block",)),
    FlagSpec("--generate-lrc", "SAME", "`--generate-lrc`", ("--generate-lrc",)),
    FlagSpec("--save-errors", "SAME", "`--save-errors`", ("--save-errors",), takes_value=True),
    FlagSpec("--print-errors", "SAME", "`--print-errors`", ("--print-errors",)),
    FlagSpec("--skip-explicit", "SAME", "`--skip-explicit`", ("--skip-explicit",)),
    FlagSpec("--detect-formats", "SAME", "`--detect-formats`", ("--detect-formats",)),
    FlagSpec(
        "--max-filename-length",
        "SAME",
        "`--max-filename-length`",
        ("--max-filename-length",),
        takes_value=True,
    ),
    FlagSpec(
        "--id3-separator", "SAME", "`--id3-separator`", ("--id3-separator",), takes_value=True
    ),
    FlagSpec("--playlist-numbering", "SAME", "`--playlist-numbering`", ("--playlist-numbering",)),
    FlagSpec("--add-unavailable", "SAME", "`--add-unavailable`", ("--add-unavailable",)),
    FlagSpec("--create-skip-file", "SAME", "`--create-skip-file`", ("--create-skip-file",)),
    FlagSpec("--respect-skip-file", "SAME", "`--respect-skip-file`", ("--respect-skip-file",)),
    FlagSpec("--log-level", "SAME", "`--log-level`", ("--log-level",), takes_value=True),
    # --- RENAME: rewritten to the v5 form -----------------------------------
    FlagSpec(
        "--scan-for-songs", "RENAME", "`--scan`", ("--scan-for-songs",), rename_to=("--scan",)
    ),
    FlagSpec(
        "--playlist-retain-track-cover",
        "RENAME",
        _RETAIN_TRACK_COVER_FORM,
        ("--playlist-retain-track-cover",),
        rename_to=("--retain-track-cover",),
    ),
    FlagSpec(
        "--sync-without-deleting",
        "RENAME",
        "`--no-delete` (on `sync`)",
        ("--sync-without-deleting",),
        rename_to=("--no-delete",),
    ),
    FlagSpec(
        "--sync-remove-lrc",
        "RENAME",
        "`--remove-lrc` (on `sync`)",
        ("--sync-remove-lrc",),
        rename_to=("--remove-lrc",),
    ),
    FlagSpec(
        "--redownload",
        "RENAME",
        "`--redownload` (on `meta`; kept)",
        ("--redownload",),
        rename_to=("--redownload",),
    ),
    FlagSpec(
        "--skip-album-art",
        "RENAME",
        "`--skip-album-art` (on `meta`; kept)",
        ("--skip-album-art",),
        rename_to=("--skip-album-art",),
    ),
    FlagSpec(
        "--force-update-metadata",
        "RENAME",
        "`--overwrite metadata`",
        ("--force-update-metadata",),
        rename_to=("--overwrite", "metadata"),
    ),
    # --- SAME (grouped) -----------------------------------------------------
    FlagSpec(
        "--host / --port",
        "SAME",
        "`--host` / `--port` (on `web`/`server`)",
        ("--host", "--port"),
        takes_value=True,
    ),
    # --- RENAME (operation → subcommand) ------------------------------------
    FlagSpec(
        "--download-ffmpeg",
        "RENAME",
        "`spotdl ffmpeg download` (operation → subcommand)",
        ("--download-ffmpeg",),
        rename_to=("ffmpeg", "download"),
        operation=True,
    ),
    FlagSpec(
        "--generate-config",
        "RENAME",
        "`spotdl config edit`",
        ("--generate-config",),
        rename_to=("config", "edit"),
        operation=True,
    ),
    FlagSpec(
        "--version / -v",
        "SAME",
        "`--version` (global eager flag printing the version; `spotdl version` also works)",
        ("--version", "-v"),
    ),
    # --- SOFT-DROP: obsolete no-ops (warn and continue) ---------------------
    FlagSpec(
        "--config",
        "SOFT-DROP",
        "config is auto-loaded from `config.toml` in v5 — the flag is unnecessary and was ignored",
        ("--config",),
        pointer="config is auto-loaded from `config.toml` in v5.",
    ),
    # --- DROP: behavior moved server-side (fail fast with a pointer) --------
    FlagSpec(
        "--audio",
        "DROP",
        "audio-source matching is server-side now; the server ranks providers and community "
        "voting refines matches",
        ("--audio",),
        pointer="audio-source matching is server-side now — the server ranks providers and "
        "community voting refines matches.",
    ),
    FlagSpec(
        "--lyrics",
        "DROP",
        "lyrics providers are server-side; use `--generate-lrc` for `.lrc`, and vote on lyrics "
        "in the TUI/web",
        ("--lyrics",),
        pointer="lyrics providers are server-side — use `--generate-lrc` for `.lrc`, and vote on "
        "lyrics in the TUI/web.",
    ),
    FlagSpec(
        "--genius-access-token",
        "DROP",
        "lyrics are fetched server-side; no client token needed",
        ("--genius-access-token",),
        pointer="lyrics are fetched server-side; no client token is needed.",
    ),
    FlagSpec(
        "--client-id / --client-secret / --auth-token / --user-auth",
        "DROP",
        "Spotify credentials are no longer client-side; the community server serves metadata "
        "(self-host: set operator creds on the server)",
        ("--client-id", "--client-secret", "--auth-token", "--user-auth"),
        takes_value=True,
        pointer="Spotify credentials are no longer client-side — the community server serves "
        "metadata (self-host: set operator creds on the server).",
    ),
    FlagSpec(
        "--cache-path / --no-cache / --use-cache-file",
        "DROP",
        "metadata caching is server-side (permanent snapshot cache)",
        ("--cache-path", "--no-cache", "--use-cache-file"),
        pointer="metadata caching is server-side (permanent snapshot cache).",
    ),
    FlagSpec(
        "--headless / --max-retries",
        "DROP",
        "Spotify auth/retry is a server concern now",
        ("--headless", "--max-retries"),
        pointer="Spotify auth and retries are a server concern now.",
    ),
    FlagSpec(
        "--search-query / --dont-filter-results / --only-verified-results / --album-type",
        "DROP",
        "matching/search tuning is server-side (versioned matcher); community voting refines "
        "results",
        ("--search-query", "--dont-filter-results", "--only-verified-results", "--album-type"),
        pointer="matching and search tuning are server-side (versioned matcher); community "
        "voting refines results.",
    ),
    FlagSpec(
        "--ytm-data",
        "DROP",
        "metadata source selection is server-side",
        ("--ytm-data",),
        pointer="metadata source selection is server-side.",
    ),
    FlagSpec(
        "--fetch-albums / --ignore-albums",
        "DROP",
        "resolve albums explicitly (`spotdl download album:<name>` / album URL)",
        ("--fetch-albums", "--ignore-albums"),
        pointer="resolve albums explicitly — `spotdl download album:<name>` or an album URL.",
    ),
    # --- SOFT-DROP ----------------------------------------------------------
    FlagSpec(
        "--preload",
        "SOFT-DROP",
        "downloads are queued and prefetched automatically in v5 — the flag was ignored",
        ("--preload",),
        pointer="downloads are queued and prefetched automatically in v5.",
    ),
    # --- DROP (continued) ---------------------------------------------------
    FlagSpec(
        "--simple-tui",
        "DROP",
        "the plain Rich progress is the default non-TTY renderer; there is no separate simple TUI",
        ("--simple-tui",),
        pointer="the plain Rich progress is the default non-TTY renderer; there is no separate "
        "simple TUI.",
    ),
    FlagSpec(
        "--log-format",
        "DROP",
        "custom logging formats were removed; use `--log-level`",
        ("--log-format",),
        pointer="custom logging formats were removed — use `--log-level`.",
    ),
    FlagSpec(
        "--profile / --check-for-updates",
        "DROP",
        "removed (use your OS profiler / `pip install -U spotdl`)",
        ("--profile", "--check-for-updates"),
        pointer="removed — use your OS profiler, or `pip install -U spotdl` to update.",
    ),
    FlagSpec(
        "--web-gui-repo / --web-gui-location / --force-update-gui",
        "DROP",
        "the web UI is bundled in the package now — no runtime GitHub fetch (spec §8)",
        ("--web-gui-repo", "--web-gui-location", "--force-update-gui"),
        pointer="the web UI is bundled in the package now — there is no runtime GitHub fetch.",
    ),
    FlagSpec(
        "--keep-alive / --keep-sessions / --web-use-output-dir / --allowed-origins",
        "DROP",
        "web-server session model changed; run `spotdl web` (embedded, single-user) or "
        "`spotdl server --mode selfhost`",
        ("--keep-alive", "--keep-sessions", "--web-use-output-dir", "--allowed-origins"),
        pointer="the web-server session model changed — run `spotdl web` (embedded, single-user) "
        "or `spotdl server --mode selfhost`.",
    ),
    FlagSpec(
        "--enable-tls / --cert-file / --key-file / --ca-file",
        "DROP",
        "terminate TLS at a reverse proxy (see the self-host deploy docs / `deploy/`)",
        ("--enable-tls", "--cert-file", "--key-file", "--ca-file"),
        pointer="terminate TLS at a reverse proxy — see the self-host deploy docs (`deploy/`).",
    ),
)


# The ``.spotdl`` v4 → v2 field table (CONTRACT G's documentation projection). The
# migration *logic* lives in ``savefile.py``; these rows only feed the guide.
SPOTDL_FIELD_TABLE: tuple[FieldSpec, ...] = (
    FieldSpec(
        "(top-level bare array)",
        "`SaveFileV2.songs[]`",
        "v4's `.spotdl` was a bare JSON array of `Song.asdict`; v5 wraps it in "
        "`{version: 2, ...}`.",
    ),
    FieldSpec("`name`", "`SaveFileSong.name`", "Track title, copied through."),
    FieldSpec("`artists`", "`SaveFileSong.artists`", "Artist list, copied through."),
    FieldSpec(
        "`duration`",
        "`SaveFileSong.duration`",
        "v4 stored **seconds**; v5 stores **milliseconds** (s → ms).",
    ),
    FieldSpec(
        "`download_url`",
        "`SaveFileSong.match.url`",
        "Moved under the per-track `match`; audio-target URL.",
    ),
    FieldSpec(
        "`list_name` / `album_name`",
        "`SaveFileV2.kind` + `.name`",
        "Used to infer `kind` (`playlist`/`album`/`single`) and the collection `name`.",
    ),
    FieldSpec(
        "(audio host of `download_url`)",
        "`SaveFileSong.match.provider`",
        "Inferred from the URL host (`youtu.be`→`youtube`, "
        "`music.youtube.com`→`youtube-music`, `soundcloud.com`→`soundcloud`, "
        "`*.bandcamp.com`→`bandcamp`, unknown→`youtube`) — never a validation failure.",
    ),
    FieldSpec(
        "(file mtime)",
        "`SaveFileV2.created_at`",
        "v4 files carry no timestamp; the loader uses the file mtime (ISO-8601).",
    ),
    FieldSpec(
        "(none)",
        "`SaveFileV2.matcher_version`",
        "`null` for migrated v4 files (no matcher provenance existed).",
    ),
    FieldSpec("(none)", "`SaveFileV2.source`", "`null` — v4 files record no originating URL."),
)


# Runtime lookup: every individual v4 token → its row (grouped rows expand).
_FLAG_LOOKUP: dict[str, FlagSpec] = {flag: spec for spec in V4_FLAG_TABLE for flag in spec.flags}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Unchanged:
    """The argv is already valid v5 — pass it straight to Typer."""


@dataclass(frozen=True)
class Rewritten:
    """The argv was normalized. ``notices`` are printed to stderr; ``argv`` runs."""

    argv: list[str]
    notices: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Dropped:
    """A DROP flag was used — ``main()`` prints the error and exits ``USAGE`` (2)."""

    flag: str
    pointer: str


ShimResult = Unchanged | Rewritten | Dropped


# ---------------------------------------------------------------------------
# Pinned message copy
# ---------------------------------------------------------------------------
def translation_note(new_argv: list[str]) -> str:
    """The one-line note printed once when a v4 invocation is translated."""
    return (
        f"note: translated a spotdl v4 invocation → `spotdl {' '.join(new_argv)}` "
        "(see the v4→v5 migration guide)."
    )


def softdrop_warning(flag: str, pointer: str) -> str:
    """The per-flag warning printed when an obsolete no-op is stripped."""
    return f"warning: `{flag}` is obsolete in spotdl v5 and was ignored — {pointer}"


def drop_message(flag: str, pointer: str) -> str:
    """The error printed (and then exit ``USAGE``) when a removed flag is used."""
    return f"error: `{flag}` was removed in spotdl v5. {pointer}"


def _is_flag(token: str) -> bool:
    return token.startswith("-") and token != "-"


def _flag_name(token: str) -> str:
    """The lookup key for ``token``: the part before ``=`` for ``--flag=value``."""
    if token.startswith("--") and "=" in token:
        return token.split("=", 1)[0]
    return token


# ---------------------------------------------------------------------------
# The shim
# ---------------------------------------------------------------------------
def translate_v4_argv(argv: list[str]) -> ShimResult:
    """Normalize a possibly-v4 ``argv`` (``sys.argv[1:]``) into the v5 form.

    Pure and side-effect free: it never prints or exits — ``main()`` renders the
    :class:`Rewritten` notices / :class:`Dropped` error. See the module docstring
    for the four row kinds and the operation-mapping rules.
    """
    if not argv:
        return Unchanged()

    tokens = list(argv)
    body: list[str] = []
    notices: list[str] = []
    op_from_flag: list[str] | None = None
    explicit_op = False
    positional_started = False
    emit_note = False

    # Known obscurity (documented, not handled): this loop does NOT treat a bare
    # ``--`` as click's "end of options" separator. A DROP flag written *after* a
    # ``--`` (``spotdl download q -- --audio``) is still matched by name and fails
    # fast, even though click would have taken it as a positional. ``--`` is rare
    # in real spotdl lines (queries/URLs don't start with ``-``), so the shim keeps
    # the single-pass table lookup rather than tracking separator state.
    i = 0
    n = len(tokens)
    while i < n:
        token = tokens[i]
        name = _flag_name(token)
        spec = _FLAG_LOOKUP.get(name)

        # An operation-flag (``--download-ffmpeg`` / ``--generate-config``) becomes
        # the leading subcommand and replaces the operation, wherever it appears.
        if spec is not None and spec.operation:
            op_from_flag = list(spec.rename_to)
            emit_note = True
            i += 1
            continue

        if spec is None:
            if _is_flag(token):
                # A flag we don't translate (a new v5 flag, or ``--help``): keep it.
                body.append(token)
                i += 1
                continue
            # A bare positional. The first one may be the operation/command.
            if not positional_started and name in V5_COMMANDS:
                explicit_op = True
            positional_started = True
            body.append(token)
            i += 1
            continue

        if spec.kind == "DROP":
            # Fail fast — drops take precedence over any renames/soft-drops seen.
            return Dropped(flag=name, pointer=spec.pointer)

        if spec.kind == "SOFT-DROP":
            notices.append(softdrop_warning(name, spec.pointer))
            i += 1
            has_inline_value = token.startswith("--") and "=" in token
            if spec.takes_value and not has_inline_value and i < n:
                i += 1  # strip the value too
            continue

        if spec.kind == "RENAME":
            body.extend(spec.rename_to)
            if tuple(spec.rename_to) != (name,):
                emit_note = True
            i += 1
            continue

        # SAME: keep the token; skip its required value so it isn't re-parsed.
        body.append(token)
        i += 1
        has_inline_value = token.startswith("--") and "=" in token
        if spec.takes_value and not has_inline_value:
            value_missing = i >= n or _is_flag(tokens[i])
            if value_missing and spec.bare_default is not None:
                # v4 allowed the bare form; keep it working (v4 parity).
                body.append(spec.bare_default)
                emit_note = True
            elif i < n:
                body.append(tokens[i])
                i += 1

    # Resolve the leading operation.
    if op_from_flag is not None:
        new_argv = op_from_flag + body
    elif explicit_op:
        new_argv = body
    elif body and _is_flag(body[0]) and _FLAG_LOOKUP.get(_flag_name(body[0])) is None:
        # A LEADING flag the shim doesn't own is a v5 global option (e.g.
        # `--api-url` / `--offline`), not a download knob. Wrapping into `download`
        # would hand that flag to a command that doesn't accept it ("No such
        # option"); leave the argv for Typer's root callback + command resolution.
        # `spotdl --api-url http://h search q` → runs `search q`, not `download`.
        new_argv = body
    elif any(not _is_flag(tok) for tok in body):
        # Bare-query sugar (`spotdl <query>` → `spotdl download <query>`): no note.
        new_argv = ["download", *body]
    else:
        # Only global flags (e.g. `--version`) — nothing to prepend.
        new_argv = body

    if emit_note:
        notices.append(translation_note(new_argv))

    if new_argv == tokens and not notices:
        return Unchanged()
    return Rewritten(argv=new_argv, notices=notices)
