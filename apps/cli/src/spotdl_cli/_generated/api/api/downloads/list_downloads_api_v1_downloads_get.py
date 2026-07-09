from http import HTTPStatus
from typing import Any, Optional, Union, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.download_list_response import DownloadListResponse
from ...models.download_status import DownloadStatus
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: Union[DownloadStatus, None, Unset] = UNSET,
    batch_id: Union[None, UUID, Unset] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_status: Union[None, Unset, str]
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, DownloadStatus):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    json_batch_id: Union[None, Unset, str]
    if isinstance(batch_id, Unset):
        json_batch_id = UNSET
    elif isinstance(batch_id, UUID):
        json_batch_id = str(batch_id)
    else:
        json_batch_id = batch_id
    params["batch_id"] = json_batch_id

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/downloads",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[DownloadListResponse, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = DownloadListResponse.from_dict(response.json())

        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[DownloadListResponse, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[DownloadStatus, None, Unset] = UNSET,
    batch_id: Union[None, UUID, Unset] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Response[Union[DownloadListResponse, HTTPValidationError]]:
    """List Downloads

     A newest-first page of jobs with optional ``status`` / ``batch_id`` filters.

    Args:
        status (Union[DownloadStatus, None, Unset]):
        batch_id (Union[None, UUID, Unset]):
        limit (Union[Unset, int]):  Default: 50.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DownloadListResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        status=status,
        batch_id=batch_id,
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
    status: Union[DownloadStatus, None, Unset] = UNSET,
    batch_id: Union[None, UUID, Unset] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[DownloadListResponse, HTTPValidationError]]:
    """List Downloads

     A newest-first page of jobs with optional ``status`` / ``batch_id`` filters.

    Args:
        status (Union[DownloadStatus, None, Unset]):
        batch_id (Union[None, UUID, Unset]):
        limit (Union[Unset, int]):  Default: 50.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DownloadListResponse, HTTPValidationError]
    """

    return sync_detailed(
        client=client,
        status=status,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[DownloadStatus, None, Unset] = UNSET,
    batch_id: Union[None, UUID, Unset] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Response[Union[DownloadListResponse, HTTPValidationError]]:
    """List Downloads

     A newest-first page of jobs with optional ``status`` / ``batch_id`` filters.

    Args:
        status (Union[DownloadStatus, None, Unset]):
        batch_id (Union[None, UUID, Unset]):
        limit (Union[Unset, int]):  Default: 50.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DownloadListResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        status=status,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[DownloadStatus, None, Unset] = UNSET,
    batch_id: Union[None, UUID, Unset] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[DownloadListResponse, HTTPValidationError]]:
    """List Downloads

     A newest-first page of jobs with optional ``status`` / ``batch_id`` filters.

    Args:
        status (Union[DownloadStatus, None, Unset]):
        batch_id (Union[None, UUID, Unset]):
        limit (Union[Unset, int]):  Default: 50.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DownloadListResponse, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
    ).parsed
