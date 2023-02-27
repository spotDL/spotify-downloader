"""
Result is a class that contains all the information about a result from search
perfoermed by audio provider.
"""

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

__all__ = ["Result"]


@dataclass(frozen=True, eq=True)
class Result:
    """
    Result is a class that contains all the information about a result from search
    perfoermed by audio provider.
    """

    # Required fields
    source: str  # Source of the result
    url: str  # URL of the result
    verified: bool  # Whether the result is from a verified source or not
    name: str  # Name of the result
    duration: float  # Duration of the result in seconds
    author: str  # Author of the result
    result_id: str  # ID of the result

    # Search related fields
    isrc_search: Optional[
        bool
    ] = None  # Whether the result is from an ISRC search or not
    search_query: Optional[str] = None  # The search query used to find the result

    # Optional fields
    artists: Optional[Tuple[str, ...]] = None
    views: Optional[int] = None
    explicit: Optional[bool] = None
    album: Optional[str] = None
    year: Optional[int] = None
    track_number: Optional[int] = None
    genre: Optional[str] = None
    lyrics: Optional[str] = None

    @classmethod
    def from_data_dump(cls, data: str) -> "Result":
        """
        Create a Result object from a data dump.

        ### Arguments
        - data: The data dump.

        ### Returns
        - The Song object.
        """

        # Create dict from json string
        data_dict = json.loads(data)

        # Return product object
        return cls(**data_dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Result":
        """
        Create a Song object from a dictionary.

        ### Arguments
        - data: The dictionary.

        ### Returns
        - The Song object.
        """

        # Return product object
        return cls(**data)

    @property
    def json(self) -> Dict[str, Any]:
        """
        Returns a dictionary of the song's data.

        ### Returns
        - The dictionary.
        """

        return asdict(self)
