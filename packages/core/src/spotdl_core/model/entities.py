from pydantic import BaseModel, ConfigDict, field_validator

from spotdl_core.model.enums import EntityType, LyricsKind, MatchStatus, ProviderId


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ArtistRef(_Frozen):
    name: str
    provider: ProviderId | None = None
    provider_id: str | None = None


class AlbumRef(_Frozen):
    name: str
    album_artist: str | None = None
    year: int | None = None
    track_count: int | None = None
    disc_count: int | None = None
    cover_url: str | None = None


class Track(_Frozen):
    name: str
    artists: tuple[str, ...]
    duration_ms: int
    album: AlbumRef | None = None
    isrc: str | None = None
    explicit: bool | None = None
    track_number: int | None = None
    disc_number: int | None = None
    genres: tuple[str, ...] = ()
    year: int | None = None
    date: str | None = None  # original release date, ISO "YYYY-MM-DD" (v4 {original-date})
    publisher: str | None = None  # label / encoded-by (v4 {publisher})
    copyright_text: str | None = None  # album copyright line
    popularity: int | None = None  # 0-100 popularity prior (POPM rating / m4a rtng source)
    cover_url: str | None = None  # track-level cover (retain-track-cover); falls back to album
    provider: ProviderId | None = None
    provider_id: str | None = None

    @field_validator("artists")
    @classmethod
    def _at_least_one_artist(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("a track needs at least one artist")
        return value

    @property
    def main_artist(self) -> str:
        return self.artists[0]


class AudioCandidate(_Frozen):
    provider: ProviderId
    provider_id: str
    url: str
    name: str
    artists: tuple[str, ...] = ()
    duration_ms: int | None = None
    album: str | None = None
    isrc: str | None = None
    verified: bool = False
    popularity: int | None = None


class FeatureVector(_Frozen):
    """Raw per-(track, candidate) signals. All *_similarity in 0..100.

    These are pure signals only. Penalty *magnitudes*, blend thresholds, and
    weights live in matching.scoring.ScoringConfig so they are versioned and
    recalibratable without touching the model.
    """

    title_similarity: float
    main_artist_similarity: float
    other_artist_similarity: float
    artist_similarity: float  # composed (main+other averaged, then v4 fixups)
    album_similarity: float | None  # None when candidate has no album
    duration_delta_s: float  # abs(track - candidate) seconds
    duration_similarity: float  # 0..100, exp-decay transform of duration_delta_s
    isrc_equal: bool
    verified_source: bool
    common_word_overlap: bool  # at least one shared title word (v4 check_common_word)
    # forbidden_words: one element per matched FORBIDDEN_WORDS *entry* (duplicates kept:
    # v4's list holds remix/reverb/live twice and penalizes per entry, so a "remix" hit
    # appears twice here).
    forbidden_words: tuple[str, ...]
    explicit_mismatch: bool
    popularity_prior: float  # 0..1, normalized candidate popularity (0.0 when unknown)


class Match(_Frozen):
    candidate: AudioCandidate
    score: float
    matcher_version: str
    status: MatchStatus = MatchStatus.AUTO
    features: FeatureVector | None = None


class Lyrics(_Frozen):
    kind: LyricsKind
    text: str
    source: ProviderId


class SearchHit(_Frozen):
    """A lightweight cross-entity search preview (universal search, spec §Phase 2).

    One row in a sectioned search result. The provider ref
    (``provider`` + ``provider_id`` + ``entity_type``) makes the hit resolvable via
    ``{provider}:{entity_type}:{provider_id}``; the remaining fields are the display
    values every entity type shares:

    * ``subtitle`` -- the artist(s) for a track/album, the owner for a playlist,
      ``None`` for an artist.
    * ``cover_url`` -- album/track cover, artist avatar, or playlist image.
    * ``year`` -- release year where a provider exposes one (tracks/albums), else
      ``None``.

    ``isrc`` is carried for tracks only (``None`` otherwise) so a fan-out can
    de-duplicate track hits by recording identity before display. A hit is a
    *preview*: it holds no track listing, matches, or lyrics -- the client resolves
    the ref for the full canonical graph.
    """

    entity_type: EntityType
    provider: ProviderId
    provider_id: str
    name: str
    subtitle: str | None = None
    cover_url: str | None = None
    year: int | None = None
    isrc: str | None = None

    @classmethod
    def from_track(cls, track: Track) -> "SearchHit":
        """Build a track ``SearchHit`` from a resolved :class:`Track`.

        The track must carry a provider ref (search results always do); the
        subtitle is its artist credit and the cover falls back to the album cover.
        """
        if track.provider is None or track.provider_id is None:
            raise ValueError("a track SearchHit needs a provider ref")
        return cls(
            entity_type=EntityType.TRACK,
            provider=track.provider,
            provider_id=track.provider_id,
            name=track.name,
            subtitle=", ".join(track.artists) or None,
            cover_url=track.cover_url or (track.album.cover_url if track.album else None),
            year=track.year,
            isrc=track.isrc,
        )
