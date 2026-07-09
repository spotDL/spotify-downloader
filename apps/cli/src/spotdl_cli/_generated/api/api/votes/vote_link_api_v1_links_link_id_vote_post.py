from http import HTTPStatus
from typing import Any, Optional, Union, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...models.vote_request import VoteRequest
from ...models.vote_response import VoteResponse
from ...types import UNSET, Response


def _get_kwargs(
    link_id: UUID,
    *,
    body: VoteRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/links/{link_id}/vote".format(
            link_id=link_id,
        ),
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, VoteResponse]]:
    if response.status_code == 200:
        response_200 = VoteResponse.from_dict(response.json())

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
) -> Response[Union[ErrorEnvelope, VoteResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    link_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: VoteRequest,
) -> Response[Union[ErrorEnvelope, VoteResponse]]:
    """Vote Link

     Up/down/retract a vote on a cross-provider entity link.

    Args:
        link_id (UUID):
        body (VoteRequest): Body of the vote endpoints: ``up`` (+1), ``down`` (-1), or
            ``retract``.

            A closed ``Literal`` so anything else is a 422 before the service runs — the
            only three verbs the state machine accepts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, VoteResponse]]
    """

    kwargs = _get_kwargs(
        link_id=link_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    link_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: VoteRequest,
) -> Optional[Union[ErrorEnvelope, VoteResponse]]:
    """Vote Link

     Up/down/retract a vote on a cross-provider entity link.

    Args:
        link_id (UUID):
        body (VoteRequest): Body of the vote endpoints: ``up`` (+1), ``down`` (-1), or
            ``retract``.

            A closed ``Literal`` so anything else is a 422 before the service runs — the
            only three verbs the state machine accepts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, VoteResponse]
    """

    return sync_detailed(
        link_id=link_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    link_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: VoteRequest,
) -> Response[Union[ErrorEnvelope, VoteResponse]]:
    """Vote Link

     Up/down/retract a vote on a cross-provider entity link.

    Args:
        link_id (UUID):
        body (VoteRequest): Body of the vote endpoints: ``up`` (+1), ``down`` (-1), or
            ``retract``.

            A closed ``Literal`` so anything else is a 422 before the service runs — the
            only three verbs the state machine accepts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, VoteResponse]]
    """

    kwargs = _get_kwargs(
        link_id=link_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    link_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: VoteRequest,
) -> Optional[Union[ErrorEnvelope, VoteResponse]]:
    """Vote Link

     Up/down/retract a vote on a cross-provider entity link.

    Args:
        link_id (UUID):
        body (VoteRequest): Body of the vote endpoints: ``up`` (+1), ``down`` (-1), or
            ``retract``.

            A closed ``Literal`` so anything else is a 422 before the service runs — the
            only three verbs the state machine accepts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, VoteResponse]
    """

    return (
        await asyncio_detailed(
            link_id=link_id,
            client=client,
            body=body,
        )
    ).parsed
