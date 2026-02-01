"""Input validation utilities for API endpoints."""

from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import HTTPException, Path, Query, status


def validate_uuid(value: str, field_name: str = "ID") -> uuid.UUID:
    """
    Validate and convert a string to a UUID.

    Args:
        value: String value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated UUID

    Raises:
        HTTPException: If validation fails
    """
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: '{value}' is not a valid UUID format",
        )


def validate_url(url: str, allowed_domains: list[str] | None = None) -> str:
    """
    Validate a URL format.

    Args:
        url: URL string to validate
        allowed_domains: Optional list of allowed domain patterns

    Returns:
        Validated URL

    Raises:
        HTTPException: If validation fails
    """
    # Basic URL pattern
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL format: '{url}'",
        )

    # Check allowed domains if specified
    if allowed_domains:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        if not any(
            domain == allowed or domain.endswith(f".{allowed}")
            for allowed in allowed_domains
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL domain not allowed. Allowed domains: {', '.join(allowed_domains)}",
            )

    return url


def validate_pagination(
    skip: int,
    limit: int,
    max_limit: int = 100,
) -> tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        max_limit: Maximum allowed limit

    Returns:
        Tuple of validated (skip, limit)

    Raises:
        HTTPException: If validation fails
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative",
        )

    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be at least 1",
        )

    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit parameter cannot exceed {max_limit}",
        )

    return skip, limit


def validate_isrc(isrc: str) -> str:
    """
    Validate an ISRC (International Standard Recording Code).

    ISRC format: CC-XXX-YY-NNNNN (12 characters without hyphens)
    - CC: Country code (2 letters)
    - XXX: Registrant code (3 alphanumeric)
    - YY: Year of reference (2 digits)
    - NNNNN: Designation code (5 digits)

    Args:
        isrc: ISRC string to validate

    Returns:
        Normalized ISRC (uppercase, no hyphens)

    Raises:
        HTTPException: If validation fails
    """
    # Remove hyphens and uppercase
    normalized = isrc.replace("-", "").upper()

    # Check length
    if len(normalized) != 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISRC: '{isrc}' must be 12 characters",
        )

    # Check format: 2 letters + 3 alphanumeric + 7 digits
    isrc_pattern = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")
    if not isrc_pattern.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISRC format: '{isrc}'",
        )

    return normalized


# Common annotated types for FastAPI path/query parameters
UUIDPath = Annotated[
    str,
    Path(
        description="Entity UUID",
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    ),
]

SkipQuery = Annotated[
    int,
    Query(
        ge=0,
        description="Number of items to skip",
    ),
]

LimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=100,
        description="Maximum number of items to return",
    ),
]

SearchQuery = Annotated[
    str,
    Query(
        min_length=1,
        max_length=200,
        description="Search query string",
    ),
]
