"""Server-side service exceptions (spec §10).

Core's :class:`~spotdl_core.providers.EntityNotFound` is intentionally thin — it
only carries the optional provider that reported an upstream entity missing. For
*server-originated* 404s (an entity GET for an id that is not in our DB) we want
the canonical entity type and id in the error envelope's ``detail``, so the
server defines its own richer exception at the raise site.

It lives in :mod:`spotdl_server.services` because it is raised by the service
layer (Tasks 8/9) yet mapped by the API layer (Task 7), and both may import it
without a layering violation.
"""

from __future__ import annotations

from uuid import UUID

from spotdl_core.model import EntityType
from spotdl_core.providers import SpotdlError

from spotdl_server.db.enums import VotableType


class NotFoundError(SpotdlError):
    """A canonical entity or votable was not found in the server DB.

    ``entity_type`` is an :class:`~spotdl_core.model.EntityType` for canonical
    entity GETs (track / album / …) or a :class:`~spotdl_server.db.enums.VotableType`
    for a votable (match / lyrics / entity_link) — both are ``StrEnum`` so the
    ``.value`` used in the message and the error-envelope ``detail`` is uniform.
    Either way the API maps it to ``404 not_found``.
    """

    def __init__(self, *, entity_type: EntityType | VotableType, entity_id: UUID | str) -> None:
        super().__init__(f"{entity_type.value} {entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


# --------------------------------------------------------------------------
# Plan 6 community-layer errors (spec §6.2/§10).
#
# All subclass ``SpotdlError`` so the single ``register_exception_handlers``
# ``SpotdlError`` handler maps them to the stable ``ErrorEnvelope`` via
# ``api/errors._status_and_code``. Each carries a safe default message (no user
# enumeration, no token contents); the raise site may override it. Declared once
# here — the authoritative home for the whole Plan 6 error vocabulary — even
# though ``OAuthEmailRequired`` (Task 6) and ``NotAnAudioTarget`` (Task 9) are
# raised by later tasks' services.
# --------------------------------------------------------------------------


class AuthRequired(SpotdlError):
    """The request needs an authenticated caller but presented none → 401."""

    def __init__(self, message: str = "authentication required") -> None:
        super().__init__(message)


class InvalidCredentials(SpotdlError):
    """Login failed — wrong password, unknown email, or a disabled account → 401.

    Deliberately generic so it never reveals whether the email exists (no user
    enumeration); every failure path raises it with the same message.
    """

    def __init__(self, message: str = "invalid email or password") -> None:
        super().__init__(message)


class InvalidToken(SpotdlError):
    """A presented token is unusable — not found, reused, or malformed → 401."""

    def __init__(self, message: str = "invalid token") -> None:
        super().__init__(message)


class TokenExpired(SpotdlError):
    """A presented token is well-formed but past its expiry → 401."""

    def __init__(self, message: str = "token expired") -> None:
        super().__init__(message)


class Forbidden(SpotdlError):
    """The caller is authenticated but lacks permission for the action → 403."""

    def __init__(self, message: str = "forbidden") -> None:
        super().__init__(message)


class EmailTaken(SpotdlError):
    """Registration hit an existing account for the normalized email → 409."""

    def __init__(self, message: str = "email already registered") -> None:
        super().__init__(message)


class TokenNotFound(SpotdlError):
    """A PAT addressed by id was not found for the caller → 404 (Task 7).

    Raised by :class:`~spotdl_server.services.pat.PatService.revoke` when the
    ownership-scoped lookup returns nothing — either the token id does not exist
    or it belongs to another user. The two are deliberately indistinguishable
    (both surface the same ``not_found``) so a caller can never probe another
    user's token ids. Maps to the existing :data:`ErrorCode.NOT_FOUND` — no new
    code in the stable error vocabulary.
    """

    def __init__(self, message: str = "token not found") -> None:
        super().__init__(message)


class OAuthEmailRequired(SpotdlError):
    """An OAuth provider returned no usable email for the account → 400 (Task 6)."""

    def __init__(self, message: str = "the OAuth provider returned no email address") -> None:
        super().__init__(message)


class NotAnAudioTarget(SpotdlError):
    """A match submission named a non-audio / non-track URL → 400 (Task 9)."""

    def __init__(self, message: str = "the submitted URL is not an audio target") -> None:
        super().__init__(message)
