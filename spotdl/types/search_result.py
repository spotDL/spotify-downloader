"""
Module for search related types.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass()
class SearchResult:
    """
    A search result.
    """

    name: str
    link: str
    duration: float
    provider: str
    owner: Optional[str]
    artists: Optional[str]
    album: Optional[str]
