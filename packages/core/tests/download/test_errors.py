import pytest
from spotdl_core.providers.errors import (
    AudioFetchFailed,
    ConversionFailed,
    DownloadFailed,
    MetadataEmbedFailed,
    PostProcessingFailed,
    SpotdlError,
)


@pytest.mark.parametrize(
    ("exc", "step"),
    [
        (AudioFetchFailed("x"), "fetch"),
        (ConversionFailed("x"), "convert"),
        (MetadataEmbedFailed("x"), "embed"),
        (PostProcessingFailed("x"), "post"),
    ],
)
def test_download_subclasses_carry_step(exc: DownloadFailed, step: str) -> None:
    assert isinstance(exc, DownloadFailed)
    assert isinstance(exc, SpotdlError)
    assert exc.step == step


def test_generic_download_failed_requires_step() -> None:
    err = DownloadFailed("boom", step="fetch")
    assert err.step == "fetch"
