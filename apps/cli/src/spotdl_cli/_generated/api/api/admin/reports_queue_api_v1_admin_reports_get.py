from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...models.paged_reports import PagedReports
from ...models.report_status import ReportStatus
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: Union[Unset, ReportStatus] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_status: Union[Unset, str] = UNSET
    if not isinstance(status, Unset):
        json_status = status.value

    params["status"] = json_status

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/admin/reports",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, PagedReports]]:
    if response.status_code == 200:
        response_200 = PagedReports.from_dict(response.json())

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
) -> Response[Union[ErrorEnvelope, PagedReports]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[Unset, ReportStatus] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorEnvelope, PagedReports]]:
    """Reports Queue

     The report queue filtered by ``status`` (default ``pending``, oldest first).

    Args:
        status (Union[Unset, ReportStatus]): Minimal review state of a metadata-correction
            ``reports`` row.
        limit (Union[Unset, int]): Maximum reports to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, PagedReports]]
    """

    kwargs = _get_kwargs(
        status=status,
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
    status: Union[Unset, ReportStatus] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorEnvelope, PagedReports]]:
    """Reports Queue

     The report queue filtered by ``status`` (default ``pending``, oldest first).

    Args:
        status (Union[Unset, ReportStatus]): Minimal review state of a metadata-correction
            ``reports`` row.
        limit (Union[Unset, int]): Maximum reports to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, PagedReports]
    """

    return sync_detailed(
        client=client,
        status=status,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[Unset, ReportStatus] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorEnvelope, PagedReports]]:
    """Reports Queue

     The report queue filtered by ``status`` (default ``pending``, oldest first).

    Args:
        status (Union[Unset, ReportStatus]): Minimal review state of a metadata-correction
            ``reports`` row.
        limit (Union[Unset, int]): Maximum reports to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, PagedReports]]
    """

    kwargs = _get_kwargs(
        status=status,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[Unset, ReportStatus] = UNSET,
    limit: Union[Unset, int] = 50,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorEnvelope, PagedReports]]:
    """Reports Queue

     The report queue filtered by ``status`` (default ``pending``, oldest first).

    Args:
        status (Union[Unset, ReportStatus]): Minimal review state of a metadata-correction
            ``reports`` row.
        limit (Union[Unset, int]): Maximum reports to return. Default: 50.
        offset (Union[Unset, int]): Rows to skip (pagination). Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, PagedReports]
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
            limit=limit,
            offset=offset,
        )
    ).parsed
