from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from spotdl_core.download import OutputFormat, RestrictMode

from spotdl_server.db.enums import OAuthProvider

if TYPE_CHECKING:
    from spotdl_core.download import DownloadConfig


class DeploymentMode(StrEnum):
    HOSTED = "hosted"
    SELFHOST = "selfhost"
    EMBEDDED = "embedded"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPOTDL_")

    mode: DeploymentMode = DeploymentMode.SELFHOST

    # SQLite file location for the selfhost/embedded default database.
    data_dir: Path = Path("~/.local/share/spotdl").expanduser()
    # Explicit database URL override (e.g. postgresql+asyncpg://...). Must name
    # an async driver when set. When None, a SQLite file under data_dir is used.
    database_url: str | None = None
    db_echo: bool = False

    # ------------------------------------------------------------------ #
    # Plan 6 — community layer (auth / voting / rate limiting)
    # ------------------------------------------------------------------ #
    # None -> derive from mode (spec §4: EMBEDDED has no auth by default).
    auth_enabled: bool | None = None
    # Required (validated at startup) when auth is active and mode is HOSTED.
    auth_secret_key: SecretStr | None = None
    access_token_ttl_seconds: int = 900  # 15 min
    refresh_token_ttl_seconds: int = 2_592_000  # 30 days
    voting_enabled: bool = True  # effective only when auth is active

    # OAuth (a provider is enabled iff both id + secret are present).
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    discord_client_id: str | None = None
    discord_client_secret: SecretStr | None = None
    # e.g. https://api.spotdl.example ; the OAuth callback is
    # {base}/api/v1/auth/oauth/{provider}/callback.
    oauth_redirect_base_url: str | None = None
    # None -> True; the server serves the SPA in every mode and hands the browser
    # back on the OAuth callback (Task 6).
    web_auth_redirect_enabled: bool | None = None
    # SPA origin for the OAuth browser handoff; None -> same origin (relative 302).
    spa_base_url: str | None = None

    # Rate limiting.
    rate_limit_enabled: bool | None = None  # None -> True iff mode is HOSTED
    redis_url: str | None = None
    client_ip_header: str | None = None  # e.g. "cf-connecting-ip"

    # ------------------------------------------------------------------ #
    # Plan 7 — server downloads (queue + delivery). Mounted only in
    # selfhost/embedded (hosted never mounts the download surface).
    # ------------------------------------------------------------------ #
    download_concurrency: int = 2
    library_path: Path | None = None  # None -> data_dir / "music"
    download_temp_dir: Path | None = None  # None -> data_dir / "temp"
    default_output_format: OutputFormat = OutputFormat.MP3
    default_bitrate: str = "auto"
    default_output_template: str = "{artists} - {title}.{output-ext}"
    ffmpeg_path: str = "ffmpeg"
    download_cookie_file: Path | None = None
    download_proxy: str | None = None
    ytdlp_args: str = ""  # shlex-tokenized into DownloadConfig.ytdlp_args
    ffmpeg_args: str = ""  # shlex-tokenized into DownloadConfig.ffmpeg_args
    # selfhost: gate downloads behind require_user; only meaningful when
    # settings.auth_active() (Plan 6).
    downloads_require_auth: bool = False
    progress_throttle_ms: int = 500
    download_drain_timeout_s: float = 30.0
    download_x_accel_prefix: str | None = None
    # None -> derive: same as downloads_require_auth.
    ws_progress_require_auth: bool | None = None

    # --- engine/session knobs (Plan-8 required amendment, folded in here): the
    # remaining Plan 4 DownloadRequest options that are server-wide configuration,
    # not per-request API fields. The CLI's embedded server (Plan 8) sets these per
    # invocation; a persistent selfhost server treats them as operator defaults —
    # consistent with ffmpeg_path/cookie_file/proxy already living in Settings.
    # Names/types/defaults match Plan 4's DownloadRequest fields (v4 parity).
    download_restrict: RestrictMode = RestrictMode.NONE
    download_max_filename_length: int | None = None
    download_id3_separator: str = "/"
    download_detect_formats: tuple[str, ...] = ()  # OutputFormat values
    download_skip_explicit: bool = False
    download_respect_skip_file: bool = False
    download_create_skip_file: bool = False
    # playlist batches: track_number := list_position, album name := playlist name
    # (v4 parity; applied at worker request-build, Task 6).
    download_playlist_numbering: bool = False
    download_retain_track_cover: bool = False
    download_add_unavailable: bool = False
    # scan effective_library_path() -> DownloadRequest.known_paths.
    download_scan_existing: bool = False

    def effective_database_url(self) -> str:
        """Resolve the async database URL used to build the engine.

        Returns the explicit ``database_url`` override when set (asserting it
        names an async driver), otherwise a ``sqlite+aiosqlite`` URL pointing at
        ``spotdl.db`` inside ``data_dir``.
        """
        if self.database_url is not None:
            assert "+aiosqlite" in self.database_url or "+asyncpg" in self.database_url, (
                "database_url must name an async driver "
                "(sqlite+aiosqlite:// or postgresql+asyncpg://)"
            )
            return self.database_url
        return f"sqlite+aiosqlite:///{self.data_dir / 'spotdl.db'}"

    def auth_active(self) -> bool:
        """Whether the community routers (auth/oauth/tokens/votes/…) are mounted.

        The embedded-mode gate (spec §4: embedded = "none (loopback only)"):
        active unless mode is EMBEDDED, or whatever ``auth_enabled`` explicitly
        forces. Startup-time gating — never a per-request conditional.
        """
        if self.auth_enabled is not None:
            return self.auth_enabled
        return self.mode is not DeploymentMode.EMBEDDED

    def rate_limit_active(self) -> bool:
        """Whether the rate-limit middleware is installed (hosted-only default)."""
        if self.rate_limit_enabled is not None:
            return self.rate_limit_enabled
        return self.mode is DeploymentMode.HOSTED

    def enabled_oauth_providers(self) -> list[OAuthProvider]:
        """OAuth providers with both a client id and secret configured."""
        providers: list[OAuthProvider] = []
        if self.github_client_id and self.github_client_secret:
            providers.append(OAuthProvider.GITHUB)
        if self.discord_client_id and self.discord_client_secret:
            providers.append(OAuthProvider.DISCORD)
        return providers

    def require_auth_secret(self) -> str:
        """Return the signing key, raising if auth is active but no key is set.

        Called once at startup (Task 5/12) so a misconfigured hosted server fails
        fast instead of minting unsigned tokens.
        """
        if self.auth_active() and self.auth_secret_key is None:
            raise RuntimeError("SPOTDL_AUTH_SECRET_KEY is required when authentication is active")
        if self.auth_secret_key is None:
            raise RuntimeError("auth secret key is not configured")
        return self.auth_secret_key.get_secret_value()

    # ------------------------------------------------------------------ #
    # Plan 7 — download helpers
    # ------------------------------------------------------------------ #
    def downloads_enabled(self) -> bool:
        """Whether the download surface (queue/WS/delivery) is mounted.

        Startup-time gating: on in selfhost/embedded, off in HOSTED (which never
        runs a local download engine — spec §4).
        """
        return self.mode is not DeploymentMode.HOSTED

    def effective_library_path(self) -> Path:
        """The on-disk root every downloaded file lives under.

        The explicit ``library_path`` override when set, else ``data_dir/music``.
        Also the path-traversal root for file delivery (CONTRACT 6).
        """
        if self.library_path is not None:
            return self.library_path
        return self.data_dir / "music"

    def effective_temp_dir(self) -> Path:
        """The engine's exclusive scratch directory (fetch/convert artifacts).

        The explicit ``download_temp_dir`` override when set, else
        ``data_dir/temp``. Swept on pool start to clear crash-orphaned partials.
        """
        if self.download_temp_dir is not None:
            return self.download_temp_dir
        return self.data_dir / "temp"

    def download_config(self) -> DownloadConfig:
        """Build the process-level :class:`~spotdl_core.download.DownloadConfig`.

        Creates the library + temp dirs (``parents=True, exist_ok=True``) and
        tokenizes the ``ytdlp_args``/``ffmpeg_args`` passthrough strings via
        ``shlex.split`` (the engine expects already-split argv tuples).
        """
        import shlex

        from spotdl_core.download import DownloadConfig

        output_dir = self.effective_library_path()
        temp_dir = self.effective_temp_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        return DownloadConfig(
            output_dir=output_dir,
            temp_dir=temp_dir,
            ffmpeg_path=self.ffmpeg_path,
            cookie_file=self.download_cookie_file,
            proxy=self.download_proxy,
            ytdlp_args=tuple(shlex.split(self.ytdlp_args)),
            ffmpeg_args=tuple(shlex.split(self.ffmpeg_args)),
        )

    def require_download_auth_consistency(self) -> None:
        """Fail fast at startup on a nonsensical download-auth configuration.

        Mirrors :meth:`require_auth_secret`: if downloads are enabled and
        ``downloads_require_auth`` is set but auth is inactive, the gate would
        silently no-op (there is no identity to require). Keys on the derived
        :meth:`auth_active` — never raw ``auth_enabled`` (whose ``None`` default
        would make the gate a silent no-op in selfhost). Called from ``create_app``.
        """
        if self.downloads_enabled() and self.downloads_require_auth and not self.auth_active():
            raise RuntimeError(
                "downloads_require_auth=True but auth is inactive "
                "(set SPOTDL_AUTH_ENABLED=true and an auth secret)"
            )
