from http import HTTPStatus
from typing import Any, Optional, Union, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.download_batch_out import DownloadBatchOut
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response


def _get_kwargs(
    batch_id: UUID,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/downloads/batches/{batch_id}".format(
            batch_id=batch_id,
        ),
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[DownloadBatchOut, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = DownloadBatchOut.from_dict(response.json())

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
) -> Response[Union[DownloadBatchOut, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    batch_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[DownloadBatchOut, HTTPValidationError]]:
    """Get Batch

     The batch's per-status tally + job listing (404 if unknown).

    Args:
        batch_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DownloadBatchOut, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        batch_id=batch_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    batch_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[DownloadBatchOut, HTTPValidationError]]:
    """Get Batch

     The batch's per-status tally + job listing (404 if unknown).

    Args:
        batch_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DownloadBatchOut, HTTPValidationError]
    """

    return sync_detailed(
        batch_id=batch_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    batch_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[DownloadBatchOut, HTTPValidationError]]:
    """Get Batch

     The batch's per-status tally + job listing (404 if unknown).

    Args:
        batch_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DownloadBatchOut, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        batch_id=batch_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    batch_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[DownloadBatchOut, HTTPValidationError]]:
    """Get Batch

     The batch's per-status tally + job listing (404 if unknown).

    Args:
        batch_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DownloadBatchOut, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            batch_id=batch_id,
            client=client,
        )
    ).parsed
