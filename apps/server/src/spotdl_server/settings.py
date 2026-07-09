from enum import StrEnum
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from spotdl_server.db.enums import OAuthProvider


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
