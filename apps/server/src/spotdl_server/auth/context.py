"""The authenticated-identity value type (CONTRACT — spec §6.2).

:class:`AuthContext` is the single, pure carrier the FastAPI auth dependency
resolves for every request: anonymous, a JWT-authenticated user, or a
PAT-authenticated CLI. It holds no FastAPI or SQLAlchemy types — the dependency
in :mod:`spotdl_server.api.deps` builds it from a verified token and (for PATs)
a loaded ``users`` row, and the routers read only these plain fields plus the
:attr:`~AuthContext.authenticated` convenience flag. Keeping it frozen and
import-light lets both ``services`` and ``api`` depend on it without a layering
violation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    """The caller's identity for one request.

    ``kind`` discriminates the three authentication outcomes; ``user_id`` is set
    for ``user``/``pat`` and ``None`` for ``anonymous``; ``token_id`` is the
    ``api_tokens.id`` only when ``kind == "pat"`` (so a route can attribute an
    action to a specific PAT). ``is_admin`` mirrors the access-token claim (or the
    PAT owner's role) — admin routes re-load the user to defeat a stale claim.
    """

    kind: Literal["anonymous", "user", "pat"]
    user_id: UUID | None = None
    is_admin: bool = False
    token_id: UUID | None = None

    @property
    def authenticated(self) -> bool:
        """Whether the caller presented a valid credential (user or PAT)."""
        return self.kind != "anonymous"


ANONYMOUS = AuthContext(kind="anonymous")
"""The shared identity for an unauthenticated request (no header / bad token)."""
