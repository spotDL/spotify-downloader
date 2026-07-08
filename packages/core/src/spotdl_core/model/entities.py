from pydantic import BaseModel, ConfigDict, field_validator

from spotdl_core.model.enums import LyricsKind, MatchStatus, ProviderId


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
    title_similarity: float
    artist_similarity: float
    album_similarity: float | None
    duration_delta_s: float
    isrc_equal: bool
    verified_source: bool
    forbidden_word_penalty: float
    explicit_mismatch: bool
    popularity_prior: float


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
