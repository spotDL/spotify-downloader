"""HTTP routers for ``/api/v1`` — thin shells over the service layer.

Each router imports only ``fastapi``, the Pydantic API schemas, the API error
envelope, and its service class (never ``sqlalchemy`` / ORM models, never a
repository) and stays ≤200 lines with no business logic — the layering rule
(spec §6), mechanically guarded by ``test_routers_under_200_lines``.

``ERROR_RESPONSES`` documents the stable :class:`~spotdl_server.api.errors.ErrorEnvelope`
as the body for every non-2xx status the handlers can emit, so the generated
OpenAPI (and the Plan 8 clients) describe errors with the real envelope shape.
"""

from __future__ import annotations

from typing import Any

from spotdl_server.api.errors import ErrorEnvelope

# Mapped onto every router so the OpenAPI error responses reference the envelope.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    429: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
    502: {"model": ErrorEnvelope},
}
