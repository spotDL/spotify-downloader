"""Golden-corpus JSON contract: pydantic models + core-model mapping helpers.

One corpus file is a JSON array of :class:`CorpusCase`; files are committed under
``packages/core/tests/matching/corpus/*.json``. These models are the single
source of truth for that on-disk format. ``to_track`` / ``to_candidates`` are the
one conversion point from corpus JSON into ``spotdl_core.model`` objects, reused
by both the recorder (Task 8) and the CI accuracy gate (Task 10).

This module is workspace tooling under ``scripts/`` — a dev consumer of
``spotdl_core``. It is deliberately outside the ``core <- server <- cli`` layer
chain and is never imported by any published package.
"""

import re
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from spotdl_core.model import AlbumRef, AudioCandidate, ProviderId, Track

ALLOWED_SOURCES: Final[frozenset[str]] = frozenset({"v4-recorded", "hand-verified"})
_KEBAB_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Sibling JSON files that live in the corpus dir but are NOT corpus case arrays
# (they are derived metadata, e.g. the v4 accuracy baseline). Corpus-file
# discovery must skip these so the plain ``corpus/*.json`` glob used by the
# validator and recorder keeps working without listing every case file by hand.
NON_CORPUS_FILENAMES: Final[frozenset[str]] = frozenset({"baseline.json"})


class _M(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorpusAlbum(_M):
    name: str
    year: int | None = None


class CorpusTrack(_M):
    name: str
    artists: tuple[str, ...] = Field(min_length=1)
    duration_ms: int
    album: CorpusAlbum | None = None
    isrc: str | None = None
    explicit: bool | None = None
    provider: str | None = None  # e.g. "spotify"
    provider_id: str | None = None


class CorpusCandidate(_M):
    provider: str  # ProviderId value, e.g. "ytmusic"
    provider_id: str
    url: str
    name: str
    artists: tuple[str, ...] = ()
    duration_ms: int | None = None
    album: str | None = None
    isrc: str | None = None
    verified: bool = False
    popularity: int | None = None  # provider-native (Spotify 0..100 or view count)


class CorpusCase(_M):
    case_id: str  # unique, kebab-case
    source: str  # "v4-recorded" | "hand-verified"
    description: str  # trap type / human note
    track: CorpusTrack
    candidates: tuple[CorpusCandidate, ...] = Field(min_length=1)
    expected_pick_index: int | None  # ground truth: index into candidates, or None
    v4_pick_index: int | None  # what v4's matcher chose on these candidates
    notes: str = ""

    @field_validator("source")
    @classmethod
    def _source_allowed(cls, value: str) -> str:
        if value not in ALLOWED_SOURCES:
            allowed = ", ".join(sorted(ALLOWED_SOURCES))
            raise ValueError(f"source must be one of {{{allowed}}}, got {value!r}")
        return value

    @field_validator("case_id")
    @classmethod
    def _case_id_kebab(cls, value: str) -> str:
        if not _KEBAB_RE.fullmatch(value):
            raise ValueError(
                f"case_id must be kebab-case (^[a-z0-9]+(-[a-z0-9]+)*$), got {value!r}"
            )
        return value

    @model_validator(mode="after")
    def _indices_in_range(self) -> "CorpusCase":
        n = len(self.candidates)
        for name, idx in (
            ("expected_pick_index", self.expected_pick_index),
            ("v4_pick_index", self.v4_pick_index),
        ):
            if idx is not None and not (0 <= idx < n):
                raise ValueError(
                    f"{name}={idx} out of range for {n} candidate(s) (must be None or in [0, {n}))"
                )
        return self


class Corpus(_M):
    cases: tuple[CorpusCase, ...]


# --------------------------------------------------------------------------- #
# Mapping helpers: corpus JSON -> core model objects (single conversion point)
# --------------------------------------------------------------------------- #


def to_track(case_track: CorpusTrack) -> Track:
    """Translate a :class:`CorpusTrack` into a ``spotdl_core.model.Track``."""
    album = (
        AlbumRef(name=case_track.album.name, year=case_track.album.year)
        if case_track.album is not None
        else None
    )
    provider = ProviderId(case_track.provider) if case_track.provider is not None else None
    return Track(
        name=case_track.name,
        artists=case_track.artists,
        duration_ms=case_track.duration_ms,
        album=album,
        isrc=case_track.isrc,
        explicit=case_track.explicit,
        provider=provider,
        provider_id=case_track.provider_id,
    )


def to_candidates(cands: tuple[CorpusCandidate, ...]) -> list[AudioCandidate]:
    """Translate corpus candidates into ``spotdl_core.model.AudioCandidate`` objects."""
    return [
        AudioCandidate(
            provider=ProviderId(c.provider),
            provider_id=c.provider_id,
            url=c.url,
            name=c.name,
            artists=c.artists,
            duration_ms=c.duration_ms,
            album=c.album,
            isrc=c.isrc,
            verified=c.verified,
            popularity=c.popularity,
        )
        for c in cands
    ]
