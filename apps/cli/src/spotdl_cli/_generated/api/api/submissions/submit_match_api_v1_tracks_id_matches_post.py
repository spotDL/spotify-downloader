from http import HTTPStatus
from typing import Any, Optional, Union, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...models.match_out import MatchOut
from ...models.submit_match_request import SubmitMatchRequest
from ...types import UNSET, Response


def _get_kwargs(
    id: UUID,
    *,
    body: SubmitMatchRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tracks/{id}/matches".format(
            id=id,
        ),
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, MatchOut]]:
    if response.status_code == 201:
        response_201 = MatchOut.from_dict(response.json())

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
) -> Response[Union[ErrorEnvelope, MatchOut]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SubmitMatchRequest,
) -> Response[Union[ErrorEnvelope, MatchOut]]:
    """Submit Match

     Submit an audio-target URL as a community match for a track (201 ``MatchOut``).

    Args:
        id (UUID):
        body (SubmitMatchRequest): Body of ``POST /tracks/{id}/matches``: the audio-target URL to
            submit.

            A single non-blank URL string; core's ``parse`` validates its shape and the
            submission service enforces that it names an audio-provider *track* (a 400
            ``unsupported_url`` / ``not_an_audio_target`` otherwise).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, MatchOut]]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SubmitMatchRequest,
) -> Optional[Union[ErrorEnvelope, MatchOut]]:
    """Submit Match

     Submit an audio-target URL as a community match for a track (201 ``MatchOut``).

    Args:
        id (UUID):
        body (SubmitMatchRequest): Body of ``POST /tracks/{id}/matches``: the audio-target URL to
            submit.

            A single non-blank URL string; core's ``parse`` validates its shape and the
            submission service enforces that it names an audio-provider *track* (a 400
            ``unsupported_url`` / ``not_an_audio_target`` otherwise).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, MatchOut]
    """

    return sync_detailed(
        id=id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SubmitMatchRequest,
) -> Response[Union[ErrorEnvelope, MatchOut]]:
    """Submit Match

     Submit an audio-target URL as a community match for a track (201 ``MatchOut``).

    Args:
        id (UUID):
        body (SubmitMatchRequest): Body of ``POST /tracks/{id}/matches``: the audio-target URL to
            submit.

            A single non-blank URL string; core's ``parse`` validates its shape and the
            submission service enforces that it names an audio-provider *track* (a 400
            ``unsupported_url`` / ``not_an_audio_target`` otherwise).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, MatchOut]]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SubmitMatchRequest,
) -> Optional[Union[ErrorEnvelope, MatchOut]]:
    """Submit Match

     Submit an audio-target URL as a community match for a track (201 ``MatchOut``).

    Args:
        id (UUID):
        body (SubmitMatchRequest): Body of ``POST /tracks/{id}/matches``: the audio-target URL to
            submit.

            A single non-blank URL string; core's ``parse`` validates its shape and the
            submission service enforces that it names an audio-provider *track* (a 400
            ``unsupported_url`` / ``not_an_audio_target`` otherwise).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, MatchOut]
    """

    return (
        await asyncio_detailed(
            id=id,
            client=client,
            body=body,
        )
    ).parsed
