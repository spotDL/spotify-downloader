from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...models.resolve_request import ResolveRequest
from ...models.resolve_response import ResolveResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: ResolveRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/resolve",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, ResolveResponse]]:
    if response.status_code == 200:
        response_200 = ResolveResponse.from_dict(response.json())

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
) -> Response[Union[ErrorEnvelope, ResolveResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ResolveRequest,
) -> Response[Union[ErrorEnvelope, ResolveResponse]]:
    """Resolve

     Resolve ``body.query`` to a canonical entity + the sources that degraded.

    Args:
        body (ResolveRequest): Body of ``POST /resolve``: a URL, ``provider:type:id`` ref, or free
            text.

            ``force=True`` bypasses the snapshot cache and refetches from the providers,
            re-merging into the same canonical entity — the client "Refresh" affordance.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, ResolveResponse]]
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
    body: ResolveRequest,
) -> Optional[Union[ErrorEnvelope, ResolveResponse]]:
    """Resolve

     Resolve ``body.query`` to a canonical entity + the sources that degraded.

    Args:
        body (ResolveRequest): Body of ``POST /resolve``: a URL, ``provider:type:id`` ref, or free
            text.

            ``force=True`` bypasses the snapshot cache and refetches from the providers,
            re-merging into the same canonical entity — the client "Refresh" affordance.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, ResolveResponse]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ResolveRequest,
) -> Response[Union[ErrorEnvelope, ResolveResponse]]:
    """Resolve

     Resolve ``body.query`` to a canonical entity + the sources that degraded.

    Args:
        body (ResolveRequest): Body of ``POST /resolve``: a URL, ``provider:type:id`` ref, or free
            text.

            ``force=True`` bypasses the snapshot cache and refetches from the providers,
            re-merging into the same canonical entity — the client "Refresh" affordance.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, ResolveResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: ResolveRequest,
) -> Optional[Union[ErrorEnvelope, ResolveResponse]]:
    """Resolve

     Resolve ``body.query`` to a canonical entity + the sources that degraded.

    Args:
        body (ResolveRequest): Body of ``POST /resolve``: a URL, ``provider:type:id`` ref, or free
            text.

            ``force=True`` bypasses the snapshot cache and refetches from the providers,
            re-merging into the same canonical entity — the client "Refresh" affordance.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, ResolveResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
