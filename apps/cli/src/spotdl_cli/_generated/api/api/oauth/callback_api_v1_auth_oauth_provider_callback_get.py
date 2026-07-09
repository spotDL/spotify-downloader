from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_envelope import ErrorEnvelope
from ...types import UNSET, Response, Unset


def _get_kwargs(
    provider: str,
    *,
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_code: Union[None, Unset, str]
    if isinstance(code, Unset):
        json_code = UNSET
    else:
        json_code = code
    params["code"] = json_code

    json_state: Union[None, Unset, str]
    if isinstance(state, Unset):
        json_state = UNSET
    else:
        json_state = state
    params["state"] = json_state

    json_error: Union[None, Unset, str]
    if isinstance(error, Unset):
        json_error = UNSET
    else:
        json_error = error
    params["error"] = json_error

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/auth/oauth/{provider}/callback".format(
            provider=provider,
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, ErrorEnvelope]]:
    if response.status_code == 200:
        response_200 = response.json()
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
) -> Response[Union[Any, ErrorEnvelope]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    provider: str,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
) -> Response[Union[Any, ErrorEnvelope]]:
    """Callback

     Finish the flow per the dual-mode contract (JSON body vs browser handoff).

    ``code``/``state``/``error`` are all optional because a provider consent
    denial is a standard OAuth2 redirect (``?error=access_denied&state=...`` with
    *no* ``code``): requiring ``code`` would 422 that real browser navigation
    before the dual-mode logic runs, stranding the user with a raw JSON body. A
    provider-supplied ``error`` (or a callback missing ``code``/``state``) is
    routed through the same ``_handoff_error``/JSON-envelope path as every other
    domain failure, as a ``provider_auth_error``.

    Args:
        provider (str):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorEnvelope]]
    """

    kwargs = _get_kwargs(
        provider=provider,
        code=code,
        state=state,
        error=error,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    provider: str,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
) -> Optional[Union[Any, ErrorEnvelope]]:
    """Callback

     Finish the flow per the dual-mode contract (JSON body vs browser handoff).

    ``code``/``state``/``error`` are all optional because a provider consent
    denial is a standard OAuth2 redirect (``?error=access_denied&state=...`` with
    *no* ``code``): requiring ``code`` would 422 that real browser navigation
    before the dual-mode logic runs, stranding the user with a raw JSON body. A
    provider-supplied ``error`` (or a callback missing ``code``/``state``) is
    routed through the same ``_handoff_error``/JSON-envelope path as every other
    domain failure, as a ``provider_auth_error``.

    Args:
        provider (str):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorEnvelope]
    """

    return sync_detailed(
        provider=provider,
        client=client,
        code=code,
        state=state,
        error=error,
    ).parsed


async def asyncio_detailed(
    provider: str,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
) -> Response[Union[Any, ErrorEnvelope]]:
    """Callback

     Finish the flow per the dual-mode contract (JSON body vs browser handoff).

    ``code``/``state``/``error`` are all optional because a provider consent
    denial is a standard OAuth2 redirect (``?error=access_denied&state=...`` with
    *no* ``code``): requiring ``code`` would 422 that real browser navigation
    before the dual-mode logic runs, stranding the user with a raw JSON body. A
    provider-supplied ``error`` (or a callback missing ``code``/``state``) is
    routed through the same ``_handoff_error``/JSON-envelope path as every other
    domain failure, as a ``provider_auth_error``.

    Args:
        provider (str):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, ErrorEnvelope]]
    """

    kwargs = _get_kwargs(
        provider=provider,
        code=code,
        state=state,
        error=error,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    provider: str,
    *,
    client: Union[AuthenticatedClient, Client],
    code: Union[None, Unset, str] = UNSET,
    state: Union[None, Unset, str] = UNSET,
    error: Union[None, Unset, str] = UNSET,
) -> Optional[Union[Any, ErrorEnvelope]]:
    """Callback

     Finish the flow per the dual-mode contract (JSON body vs browser handoff).

    ``code``/``state``/``error`` are all optional because a provider consent
    denial is a standard OAuth2 redirect (``?error=access_denied&state=...`` with
    *no* ``code``): requiring ``code`` would 422 that real browser navigation
    before the dual-mode logic runs, stranding the user with a raw JSON body. A
    provider-supplied ``error`` (or a callback missing ``code``/``state``) is
    routed through the same ``_handoff_error``/JSON-envelope path as every other
    domain failure, as a ``provider_auth_error``.

    Args:
        provider (str):
        code (Union[None, Unset, str]):
        state (Union[None, Unset, str]):
        error (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, ErrorEnvelope]
    """

    return (
        await asyncio_detailed(
            provider=provider,
            client=client,
            code=code,
            state=state,
            error=error,
        )
    ).parsed
