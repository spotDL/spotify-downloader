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


class NotFoundError(SpotdlError):
    """A canonical entity was not found in the server DB."""

    def __init__(self, *, entity_type: EntityType, entity_id: UUID | str) -> None:
        super().__init__(f"{entity_type.value} {entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id
