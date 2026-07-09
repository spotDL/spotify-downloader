from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.download_submit_request import DownloadSubmitRequest
from ...models.download_submit_response import DownloadSubmitResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: DownloadSubmitRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/downloads",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[DownloadSubmitResponse, HTTPValidationError]]:
    if response.status_code == 201:
        response_201 = DownloadSubmitResponse.from_dict(response.json())

        return response_201
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[DownloadSubmitResponse, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: DownloadSubmitRequest,
) -> Response[Union[DownloadSubmitResponse, HTTPValidationError]]:
    """Submit Download

     Resolve + expand a submission into a queued batch, then enqueue + announce.

    ``NoMatchFound`` (track with no viable match) → 404; ``UnsupportedBatchEntity``
    (e.g. an artist url) → 400 — both via the global handlers. The pool receives
    the ids and ``job_queued`` frames go out only after the service committed.

    Args:
        body (DownloadSubmitRequest): Body of ``POST /downloads``: what and how to download.

            ``query`` is a URL, ``provider:type:id`` ref, or free text (a single track);
            an album/playlist URL is expanded server-side into N jobs. The ``None``
            engine fields fall back to the server's configured defaults at submit time.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DownloadSubmitResponse, HTTPValidationError]]
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
    body: DownloadSubmitRequest,
) -> Optional[Union[DownloadSubmitResponse, HTTPValidationError]]:
    """Submit Download

     Resolve + expand a submission into a queued batch, then enqueue + announce.

    ``NoMatchFound`` (track with no viable match) → 404; ``UnsupportedBatchEntity``
    (e.g. an artist url) → 400 — both via the global handlers. The pool receives
    the ids and ``job_queued`` frames go out only after the service committed.

    Args:
        body (DownloadSubmitRequest): Body of ``POST /downloads``: what and how to download.

            ``query`` is a URL, ``provider:type:id`` ref, or free text (a single track);
            an album/playlist URL is expanded server-side into N jobs. The ``None``
            engine fields fall back to the server's configured defaults at submit time.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DownloadSubmitResponse, HTTPValidationError]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: DownloadSubmitRequest,
) -> Response[Union[DownloadSubmitResponse, HTTPValidationError]]:
    """Submit Download

     Resolve + expand a submission into a queued batch, then enqueue + announce.

    ``NoMatchFound`` (track with no viable match) → 404; ``UnsupportedBatchEntity``
    (e.g. an artist url) → 400 — both via the global handlers. The pool receives
    the ids and ``job_queued`` frames go out only after the service committed.

    Args:
        body (DownloadSubmitRequest): Body of ``POST /downloads``: what and how to download.

            ``query`` is a URL, ``provider:type:id`` ref, or free text (a single track);
            an album/playlist URL is expanded server-side into N jobs. The ``None``
            engine fields fall back to the server's configured defaults at submit time.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DownloadSubmitResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: DownloadSubmitRequest,
) -> Optional[Union[DownloadSubmitResponse, HTTPValidationError]]:
    """Submit Download

     Resolve + expand a submission into a queued batch, then enqueue + announce.

    ``NoMatchFound`` (track with no viable match) → 404; ``UnsupportedBatchEntity``
    (e.g. an artist url) → 400 — both via the global handlers. The pool receives
    the ids and ``job_queued`` frames go out only after the service committed.

    Args:
        body (DownloadSubmitRequest): Body of ``POST /downloads``: what and how to download.

            ``query`` is a URL, ``provider:type:id`` ref, or free text (a single track);
            an album/playlist URL is expanded server-side into N jobs. The ``None``
            engine fields fall back to the server's configured defaults at submit time.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DownloadSubmitResponse, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
