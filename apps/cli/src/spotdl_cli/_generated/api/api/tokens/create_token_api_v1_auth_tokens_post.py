from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_pat_request import CreatePatRequest
from ...models.error_envelope import ErrorEnvelope
from ...models.pat_created_response import PatCreatedResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: CreatePatRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/auth/tokens",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, PatCreatedResponse]]:
    if response.status_code == 201:
        response_201 = PatCreatedResponse.from_dict(response.json())

        return response_201
    if response.status_code == 400:
        response_400 = ErrorEnvelope.from_dict(response.json())

        return response_400
    if response.status_code == 401:
        response_401 = ErrorEnvelope.from_dict(response.json())

        return response_401
    if response.status_code == 403:
        response_403 = ErrorEnvelope.from_dict(response.json())

        return response_403
    if response.status_code == 404:
        response_404 = ErrorEnvelope.from_dict(response.json())

        return response_404
    if response.status_code == 409:
        response_409 = ErrorEnvelope.from_dict(response.json())

        return response_409
    if response.status_code == 422:
        response_422 = ErrorEnvelope.from_dict(response.json())

        return response_422
    if response.status_code == 429:
        response_429 = ErrorEnvelope.from_dict(response.json())

        return response_429
    if response.status_code == 500:
        response_500 = ErrorEnvelope.from_dict(response.json())

        return response_500
    if response.status_code == 502:
        response_502 = ErrorEnvelope.from_dict(response.json())

        return response_502
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorEnvelope, PatCreatedResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreatePatRequest,
) -> Response[Union[ErrorEnvelope, PatCreatedResponse]]:
    """Create Token

     Mint a PAT for the caller; the full secret is returned **only here**.

    Args:
        body (CreatePatRequest): Body of ``POST /auth/tokens``: mint a personal access token for
            the CLI.

            ``name`` is a required non-blank label (1–255 chars, matching the column
            width). ``expires_in_days`` is optional — when omitted the PAT never expires
            (``expires_at = NULL``); when given it must be a positive integer and the
            router converts it to an absolute ``expires_at`` via the shared clock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, PatCreatedResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreatePatRequest,
) -> Optional[Union[ErrorEnvelope, PatCreatedResponse]]:
    """Create Token

     Mint a PAT for the caller; the full secret is returned **only here**.

    Args:
        body (CreatePatRequest): Body of ``POST /auth/tokens``: mint a personal access token for
            the CLI.

            ``name`` is a required non-blank label (1–255 chars, matching the column
            width). ``expires_in_days`` is optional — when omitted the PAT never expires
            (``expires_at = NULL``); when given it must be a positive integer and the
            router converts it to an absolute ``expires_at`` via the shared clock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, PatCreatedResponse]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreatePatRequest,
) -> Response[Union[ErrorEnvelope, PatCreatedResponse]]:
    """Create Token

     Mint a PAT for the caller; the full secret is returned **only here**.

    Args:
        body (CreatePatRequest): Body of ``POST /auth/tokens``: mint a personal access token for
            the CLI.

            ``name`` is a required non-blank label (1–255 chars, matching the column
            width). ``expires_in_days`` is optional — when omitted the PAT never expires
            (``expires_at = NULL``); when given it must be a positive integer and the
            router converts it to an absolute ``expires_at`` via the shared clock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, PatCreatedResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: CreatePatRequest,
) -> Optional[Union[ErrorEnvelope, PatCreatedResponse]]:
    """Create Token

     Mint a PAT for the caller; the full secret is returned **only here**.

    Args:
        body (CreatePatRequest): Body of ``POST /auth/tokens``: mint a personal access token for
            the CLI.

            ``name`` is a required non-blank label (1–255 chars, matching the column
            width). ``expires_in_days`` is optional — when omitted the PAT never expires
            (``expires_at = NULL``); when given it must be a positive integer and the
            router converts it to an absolute ``expires_at`` via the shared clock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, PatCreatedResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
