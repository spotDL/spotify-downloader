"""Pure-stdlib text matching used to rank lyrics search results.

This helper depends only on the standard library (``re`` + ``difflib``), so it
cannot break provider isolation the way a scraper dependency could: it has no
third-party imports and never touches the network. Each lyrics provider uses it
to pick the search hit whose title best matches the requested track.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

__all__ = ["similarity", "slugify"]

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase ``text`` and collapse every non-alphanumeric run to a space."""
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def similarity(a: str, b: str) -> float:
    """Return a 0.0-1.0 similarity ratio between the slugs of ``a`` and ``b``."""
    return SequenceMatcher(None, slugify(a), slugify(b)).ratio()
