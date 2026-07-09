"""Public-surface tests for the finalized ``spotdl_core.download`` package.

These lock the package's public API (spec §5.4; the surface Plan 7's server
worker imports): the full re-export set is present, ``__all__`` is sorted, every
advertised name actually resolves, and — crucially — importing the package (and
the ``build_default_engine`` wiring helper) never pulls in ``yt_dlp`` or
``mutagen`` or otherwise touches the network / ffmpeg. Those heavy, blocking
dependencies are imported lazily inside the collaborators' call paths, so a
consumer that only needs the types pays nothing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# The exact public names Plan 7 (and the CLI, Plan 8) rely on. This is a
# *subset* assertion: the package may re-export more (concrete steps, preset
# tables), but every one of these MUST be present.
REQUIRED_EXPORTS = frozenset(
    {
        # entry points
        "DownloadEngine",
        "build_default_engine",
        # request / config / context / outcome
        "DownloadRequest",
        "DownloadConfig",
        "DownloadContext",
        "DownloadOutcome",
        "OutcomeStatus",
        # enums / value types
        "OutputFormat",
        "OverwriteMode",
        "RestrictMode",
        "SkipReason",
        "Bitrate",
        "BITRATE_AUTO",
        "BITRATE_DISABLE",
        # progress seam
        "ProgressEvent",
        "ProgressPhase",
        "ProgressCallback",
        "Step",
        # collaborator protocols / results
        "Fetcher",
        "FetchResult",
        "CoverDownloader",
        "SyncedLyricsSearch",
        "SponsorBlock",
        # error taxonomy (download subclasses)
        "DownloadFailed",
        "AudioFetchFailed",
        "ConversionFailed",
        "MetadataEmbedFailed",
        "PostProcessingFailed",
    }
)


def test_all_contains_required_exports() -> None:
    import spotdl_core.download as dl

    missing = REQUIRED_EXPORTS - set(dl.__all__)
    assert not missing, f"missing from __all__: {sorted(missing)}"


def test_all_is_sorted() -> None:
    import spotdl_core.download as dl

    assert list(dl.__all__) == sorted(dl.__all__)


def test_every_exported_name_resolves() -> None:
    import spotdl_core.download as dl

    for name in dl.__all__:
        assert hasattr(dl, name), f"__all__ advertises {name!r} but it is not importable"


def test_build_default_engine_is_callable() -> None:
    import spotdl_core.download as dl

    assert callable(dl.build_default_engine)


def test_import_does_not_touch_network_or_ffmpeg() -> None:
    """Importing the package (and referencing ``build_default_engine``) must not
    import the heavy blocking deps ``yt_dlp`` / ``mutagen``.

    Run in a *fresh* interpreter so nothing another test imported pollutes
    ``sys.modules``. This is the machine-check behind the brief's "lazy imports"
    requirement: a consumer importing the types pays no network/ffmpeg cost.
    """
    script = (
        "import sys\n"
        "import spotdl_core.download as dl\n"
        "assert callable(dl.build_default_engine)\n"
        "leaked = [m for m in ('yt_dlp', 'mutagen') if m in sys.modules]\n"
        "assert not leaked, leaked\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[4],
    )
    assert result.returncode == 0, result.stderr
