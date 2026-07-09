from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...models.paged_users import PagedUsers
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/admin/users",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, PagedUsers]]:
    if response.status_code == 200:
        response_200 = PagedUsers.from_dict(response.json())

        return response_200
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
) -> Response[Union[ErrorEnvelope, PagedUsers]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorEnvelope, PagedUsers]]:
    """List Users

     List users, newest first, with the full ``total`` count for pagination.

    Args:
        limit (Union[Unset, int]): Maximum users to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, PagedUsers]]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorEnvelope, PagedUsers]]:
    """List Users

     List users, newest first, with the full ``total`` count for pagination.

    Args:
        limit (Union[Unset, int]): Maximum users to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, PagedUsers]
    """

    return sync_detailed(
        client=client,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorEnvelope, PagedUsers]]:
    """List Users

     List users, newest first, with the full ``total`` count for pagination.

    Args:
        limit (Union[Unset, int]): Maximum users to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, PagedUsers]]
    """

    kwargs = _get_kwargs(
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorEnvelope, PagedUsers]]:
    """List Users

     List users, newest first, with the full ``total`` count for pagination.

    Args:
        limit (Union[Unset, int]): Maximum users to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, PagedUsers]
    """

    return (
        await asyncio_detailed(
            client=client,
            limit=limit,
            offset=offset,
        )
    ).parsed
