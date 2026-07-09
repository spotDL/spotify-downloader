"""Re-export shim for the checked-in generated client (Plan 8 Task 1).

Hand-written (held to standards); the sibling ``api`` package and ``ws_models``
module are generator output (``make clients``) and are ruff/mypy-excluded. This
shim gives the hand-written ``SpotdlClient`` façade one stable import surface:
the HTTP client classes and the WS message models.
"""

from . import ws_models
from .api import AuthenticatedClient, Client

__all__ = ["AuthenticatedClient", "Client", "ws_models"]
