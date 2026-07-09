# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "rapidfuzz>=3.10.1,<4",
#     "python-slugify[unidecode]>=8.0.4,<9",
#     "pykakasi>=2.3.0,<3",
#     "yt-dlp>=2025.09.26,<2027",
#     "spotipy>=2.24.0,<3",
#     "requests>=2.32.3,<3",
#     "rich>=13.9.4,<14",
#     "typing_extensions>=4.0,<5",
#     "ytmusicapi>=1.11.1,<2",      # drives the real YTMusic search (ONLINE)
# ]
# ///
"""ONLINE, one-shot maintainer tool: harvest real v4 candidate sets into corpus JSON.

**This script is excluded from CI and from ``make check``.** It hits the network
(Spotify metadata + YouTube Music search) and needs Spotify API credentials. It is
run by a maintainer once to seed/refresh the golden corpus; the offline recorder
(``record_v4.py``) then fills the picks, and the CI accuracy gate consumes the
result. Never import this module from the test suite.

What it does
------------
1. Reads seed Spotify track URLs from v4's ``tests/test_matching.py`` (the ~40
   curated URLs plus the commented-out extras), or from ``--urls-file``.
2. For each track: ``Song.from_url`` (Spotify) -> v4 ``Song``; then drives v4's
   own ``YouTubeMusic`` provider to fetch the real ``Result`` candidate set
   (songs + videos filters, and an ISRC search when available).
3. Serialises each ``Result`` to a ``CorpusCandidate`` and each ``Song`` to a
   ``CorpusTrack``, emitting provisional ``source="v4-recorded"`` cases with
   ``expected_pick_index``/``v4_pick_index`` left ``null`` for the recorder.

Usage::

    export SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=...
    uv run --script scripts/corpus/harvest.py -o packages/core/tests/matching/corpus/harvested.json
    # then fill picks offline:
    uv run --script scripts/corpus/record_v4.py packages/core/tests/matching/corpus/harvested.json

``--fetch-views`` additionally resolves each candidate's view count via yt-dlp
(``provider.get_views``) into ``popularity`` -- accurate but slow (one metadata
extract per candidate). Without it, ``popularity`` stays ``null`` and the recorder
treats views as absent (its no-variance tiebreak path).

Note on cassettes: v4 ships VCR cassettes under
``tests/providers/audio/cassettes/test_ytmusic/*.yaml``; a maintainer wanting to
reduce live YTMusic calls can replay those instead. That replay path is not wired
here -- this harvester talks to the live provider -- but it is a supported manual
alternative documented in ``scripts/corpus/README.md``.
"""

import argparse
import json
import os
import re
import sys
import types
from pathlib import Path
from typing import Any

V4 = Path("~/Projects/xnetcat/spotdl-v4-reference").expanduser()
_SPOTIFY_TRACK_RE = re.compile(r"open\.spotify\.com/track/[A-Za-z0-9]+")


def _stub_pkg(name: str, path: Path) -> None:
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)]  # make it a package without running __init__.py
    sys.modules[name] = mod


def _bootstrap_v4() -> None:
    """Register stub parent packages so v4 leaf modules import without the app __init__."""
    if str(V4) not in sys.path:
        sys.path.insert(0, str(V4))
    _stub_pkg("spotdl", V4 / "spotdl")
    _stub_pkg("spotdl.utils", V4 / "spotdl" / "utils")
    _stub_pkg("spotdl.types", V4 / "spotdl" / "types")
    _stub_pkg("spotdl.providers", V4 / "spotdl" / "providers")
    _stub_pkg("spotdl.providers.audio", V4 / "spotdl" / "providers" / "audio")


def read_seed_urls(urls_file: Path | None) -> list[str]:
    """Return de-duplicated Spotify track URLs (seed order preserved).

    Defaults to scraping v4's ``tests/test_matching.py`` (active + commented-out
    URLs); an explicit ``--urls-file`` (one URL per line, ``#`` comments allowed)
    overrides that.
    """
    if urls_file is not None:
        text = urls_file.read_text(encoding="utf-8")
        raw = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    else:
        source = V4 / "tests" / "test_matching.py"
        raw = [f"https://{m.group(0)}" for m in _SPOTIFY_TRACK_RE.finditer(source.read_text())]

    seen: set[str] = set()
    urls: list[str] = []
    for url in raw:
        canonical = f"https://{_SPOTIFY_TRACK_RE.search(url).group(0)}"  # type: ignore[union-attr]
        if canonical not in seen:
            seen.add(canonical)
            urls.append(canonical)
    return urls


def _case_id(song: Any, existing: set[str]) -> str:
    from slugify import slugify

    base = slugify(f"{song.artist}-{song.name}")[:60] or "track"
    case_id = base
    suffix = 2
    while case_id in existing:
        case_id = f"{base}-{suffix}"
        suffix += 1
    existing.add(case_id)
    return case_id


def _track_json(song: Any) -> dict[str, Any]:
    return {
        "name": song.name,
        "artists": list(song.artists),
        "duration_ms": round(song.duration * 1000),
        "album": {"name": song.album_name, "year": song.year or None},
        "isrc": song.isrc,
        "explicit": song.explicit,
        "provider": "spotify",
        "provider_id": song.song_id,
    }


def _candidate_json(result: Any) -> dict[str, Any]:
    return {
        "provider": "ytmusic",
        "provider_id": result.result_id,
        "url": result.url,
        "name": result.name,
        "artists": list(result.artists) if result.artists else [],
        "duration_ms": round(result.duration * 1000) if result.duration else None,
        "album": result.album,
        "isrc": None,  # YTMusic search results carry no per-candidate ISRC
        "verified": bool(result.verified),
        "popularity": result.views,  # filled by --fetch-views when requested
    }


def _gather_candidates(provider: Any, song: Any) -> list[Any]:
    """Collect the deduped v4 ``Result`` candidate set for one song (songs+videos+ISRC)."""
    from spotdl.utils.formatter import (  # type: ignore[import-not-found]
        create_song_title,
    )

    search_query = create_song_title(song.name, song.artists).lower()

    results: list[Any] = []
    seen: set[str] = set()

    def _add(items: list[Any]) -> None:
        for result in items:
            if result.url not in seen:
                seen.add(result.url)
                results.append(result)

    for opts in provider.GET_RESULTS_OPTS:
        _add(provider.get_results(search_query, **opts))
    if song.isrc and provider.SUPPORTS_ISRC:
        _add(provider.get_results(song.isrc))

    return results


def harvest(
    urls: list[str],
    *,
    fetch_views: bool,
) -> list[dict[str, Any]]:
    """Fetch candidate sets for every URL and return provisional corpus-case dicts."""
    from spotdl.providers.audio.ytmusic import (  # type: ignore[import-not-found]
        YouTubeMusic,
    )
    from spotdl.types.song import Song  # type: ignore[import-not-found]

    provider = YouTubeMusic()

    cases: list[dict[str, Any]] = []
    existing_ids: set[str] = set()
    for url in urls:
        try:
            song = Song.from_url(url)
        except Exception as exc:  # noqa: BLE001 - one bad URL must not abort the run
            print(f"warning: skipping {url}: {exc}", file=sys.stderr)
            continue

        results = _gather_candidates(provider, song)
        if not results:
            print(f"warning: no candidates for {url}", file=sys.stderr)
            continue

        if fetch_views:
            for result in results:
                if result.views is None:
                    try:
                        object.__setattr__(result, "views", provider.get_views(result.url))
                    except Exception as exc:  # noqa: BLE001
                        print(f"warning: get_views failed for {result.url}: {exc}", file=sys.stderr)

        cases.append(
            {
                "case_id": _case_id(song, existing_ids),
                "source": "v4-recorded",
                "description": f"harvested from {url}",
                "track": _track_json(song),
                "candidates": [_candidate_json(r) for r in results],
                "expected_pick_index": None,
                "v4_pick_index": None,
                "notes": "",
            }
        )
        print(f"{url}: {len(results)} candidates", file=sys.stderr)

    return cases


def _init_spotify() -> None:
    from spotdl.utils.spotify import SpotifyClient  # type: ignore[import-not-found]

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "error: set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in the environment"
        )
    SpotifyClient.init(client_id=client_id, client_secret=client_secret, no_cache=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harvest.py",
        description="ONLINE: harvest real v4 candidate sets into provisional corpus JSON.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Path to write the provisional corpus JSON array.",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        default=None,
        help="Optional file of Spotify track URLs (one per line); defaults to v4's tests.",
    )
    parser.add_argument(
        "--fetch-views",
        action="store_true",
        help="Resolve each candidate's view count via yt-dlp into popularity (slow).",
    )
    args = parser.parse_args(argv)

    _bootstrap_v4()
    _init_spotify()

    urls = read_seed_urls(args.urls_file)
    if not urls:
        print("error: no seed URLs found", file=sys.stderr)
        return 1
    print(f"harvesting {len(urls)} track(s)...", file=sys.stderr)

    cases = harvest(urls, fetch_views=args.fetch_views)
    args.output.write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} case(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
