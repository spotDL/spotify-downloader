from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...models.register_request import RegisterRequest
from ...models.token_response import TokenResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: RegisterRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/auth/register",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorEnvelope, TokenResponse]]:
    if response.status_code == 201:
        response_201 = TokenResponse.from_dict(response.json())

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
) -> Response[Union[ErrorEnvelope, TokenResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: RegisterRequest,
) -> Response[Union[ErrorEnvelope, TokenResponse]]:
    """Register

     Create an account (no email verification in v1) and issue its first tokens.

    Args:
        body (RegisterRequest): Body of ``POST /auth/register``.

            ``password`` policy (argon2id, so bcrypt's 72-byte trap does not apply — the
            max only bounds hashing cost): 8–128 characters, enforced here so a weak or
            abusively long password is rejected before it reaches the service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, TokenResponse]]
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
    body: RegisterRequest,
) -> Optional[Union[ErrorEnvelope, TokenResponse]]:
    """Register

     Create an account (no email verification in v1) and issue its first tokens.

    Args:
        body (RegisterRequest): Body of ``POST /auth/register``.

            ``password`` policy (argon2id, so bcrypt's 72-byte trap does not apply — the
            max only bounds hashing cost): 8–128 characters, enforced here so a weak or
            abusively long password is rejected before it reaches the service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, TokenResponse]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: RegisterRequest,
) -> Response[Union[ErrorEnvelope, TokenResponse]]:
    """Register

     Create an account (no email verification in v1) and issue its first tokens.

    Args:
        body (RegisterRequest): Body of ``POST /auth/register``.

            ``password`` policy (argon2id, so bcrypt's 72-byte trap does not apply — the
            max only bounds hashing cost): 8–128 characters, enforced here so a weak or
            abusively long password is rejected before it reaches the service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorEnvelope, TokenResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: RegisterRequest,
) -> Optional[Union[ErrorEnvelope, TokenResponse]]:
    """Register

     Create an account (no email verification in v1) and issue its first tokens.

    Args:
        body (RegisterRequest): Body of ``POST /auth/register``.

            ``password`` policy (argon2id, so bcrypt's 72-byte trap does not apply — the
            max only bounds hashing cost): 8–128 characters, enforced here so a weak or
            abusively long password is rejected before it reaches the service.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorEnvelope, TokenResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
