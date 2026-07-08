import pytest
from spotdl_core.model import ProviderId
from spotdl_core.providers import (
    ConversionFailed,
    DownloadFailed,
    EntityNotFound,
    MetadataEmbedFailed,
    NoMatchFound,
    ProviderAuthError,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    SpotdlError,
    UnsupportedURL,
)


@pytest.mark.parametrize(
    "exc",
    [ProviderError, ProviderUnavailable, ProviderAuthError, RateLimited, EntityNotFound],
)
def test_provider_errors_are_spotdl_errors(exc: type[Exception]) -> None:
    assert issubclass(exc, ProviderError)
    assert issubclass(exc, SpotdlError)


def test_unsupported_url_and_no_match_are_spotdl_but_not_provider_errors() -> None:
    assert issubclass(UnsupportedURL, SpotdlError)
    assert issubclass(NoMatchFound, SpotdlError)
    assert not issubclass(UnsupportedURL, ProviderError)


def test_provider_error_carries_provider_id() -> None:
    err = ProviderUnavailable("down", provider=ProviderId.SPOTIFY)
    assert err.provider is ProviderId.SPOTIFY
    assert str(err) == "down"


def test_rate_limited_carries_retry_after() -> None:
    err = RateLimited(provider=ProviderId.MUSICBRAINZ, retry_after=1.5)
    assert err.retry_after == 1.5


def test_download_errors_carry_step() -> None:
    assert issubclass(ConversionFailed, DownloadFailed)
    assert issubclass(MetadataEmbedFailed, DownloadFailed)
    assert issubclass(DownloadFailed, SpotdlError)
    assert ConversionFailed().step == "convert"
    assert MetadataEmbedFailed().step == "embed"
    assert DownloadFailed(step="fetch").step == "fetch"
