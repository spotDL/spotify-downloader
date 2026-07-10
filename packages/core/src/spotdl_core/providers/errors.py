"""Typed exception taxonomy for spotDL core (spec §10).

This is the first consumer, so the full set is defined here. The provider
subset is raised in this plan; the download subset is defined here as the
shared taxonomy root and raised in Plan 4. The server (Plan 5+) maps these to
the stable API error envelope {code, message, detail}.
"""

from __future__ import annotations

from spotdl_core.model import ProviderId


class SpotdlError(Exception):
    """Root of the spotDL exception hierarchy."""


# --- provider layer -------------------------------------------------------


class ProviderError(SpotdlError):
    """Base for provider-layer failures; carries the provider id when known."""

    def __init__(self, message: str = "", *, provider: ProviderId | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class ProviderUnavailable(ProviderError):
    """Provider unreachable, down, dependency import failed, or repeated 5xx."""


class ProviderNotConfigured(ProviderUnavailable):
    """An OPTIONAL provider the operator never configured (e.g. no API key).

    A deliberate absence, not an outage: consumers must NOT surface it as a
    degraded source (a permanent "sources unavailable" banner for a provider the
    user never enabled would be noise), while ``registry.get``/``capable`` still
    treat it as unavailable.
    """


class ProviderAuthError(ProviderError):
    """Authentication/token acquisition failed (401/403, bad creds, TOTP failure)."""


class RateLimited(ProviderError):
    """Provider returned 429 after retries were exhausted."""

    def __init__(
        self,
        message: str = "",
        *,
        provider: ProviderId | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, provider=provider)
        self.retry_after = retry_after


class EntityNotFound(ProviderError):
    """The requested entity id/URL resolved to nothing (404 or empty result)."""


class UnsupportedURL(SpotdlError):
    """A URL or `provider:type:id` string could not be parsed to a known ref."""


class NoMatchFound(SpotdlError):
    """Search/match produced no candidate for the given track."""


# --- download layer (raised in Plan 4; defined here as the shared taxonomy) --


class DownloadFailed(SpotdlError):
    """A download-pipeline step failed. `step` names the failing step."""

    def __init__(self, message: str = "", *, step: str) -> None:
        super().__init__(message)
        self.step = step


class ConversionFailed(DownloadFailed):
    """ffmpeg conversion failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="convert")


class MetadataEmbedFailed(DownloadFailed):
    """Tag/metadata embedding failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="embed")


class AudioFetchFailed(DownloadFailed):
    """yt-dlp failed to fetch/download the chosen audio candidate."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="fetch")


class PostProcessingFailed(DownloadFailed):
    """A post-processing step (lrc/m3u/archive/SponsorBlock) failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, step="post")
