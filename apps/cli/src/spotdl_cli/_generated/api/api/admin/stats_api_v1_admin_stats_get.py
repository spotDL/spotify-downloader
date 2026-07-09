from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.admin_stats_response import AdminStatsResponse
from ...models.error_envelope import ErrorEnvelope
from ...types import UNSET, Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/admin/stats",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[AdminStatsResponse, ErrorEnvelope]]:
    if response.status_code == 200:
        response_200 = AdminStatsResponse.from_dict(response.json())

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
) -> Response[Union[AdminStatsResponse, ErrorEnvelope]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[AdminStatsResponse, ErrorEnvelope]]:
    """Stats

     Aggregate community-health counts for the admin dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AdminStatsResponse, ErrorEnvelope]]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[AdminStatsResponse, ErrorEnvelope]]:
    """Stats

     Aggregate community-health counts for the admin dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AdminStatsResponse, ErrorEnvelope]
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[AdminStatsResponse, ErrorEnvelope]]:
    """Stats

     Aggregate community-health counts for the admin dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AdminStatsResponse, ErrorEnvelope]]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[AdminStatsResponse, ErrorEnvelope]]:
    """Stats

     Aggregate community-health counts for the admin dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AdminStatsResponse, ErrorEnvelope]
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
