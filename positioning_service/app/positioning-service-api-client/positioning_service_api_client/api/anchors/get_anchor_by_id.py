from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.anchor import Anchor
from ...types import Response


def _get_kwargs(
    anchor_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/anchors/{anchor_id}".format(
            anchor_id=quote(str(anchor_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Anchor | Any | None:
    if response.status_code == 200:
        response_200 = Anchor.from_dict(response.json())

        return response_200

    if response.status_code == 404:
        response_404 = cast(Any, None)
        return response_404

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Anchor | Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    anchor_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Anchor | Any]:
    """Получение информации о конкретном анкере

     Возвращает детальную конфигурацию анкера по его ID.

    Args:
        anchor_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Anchor | Any]
    """

    kwargs = _get_kwargs(
        anchor_id=anchor_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    anchor_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Anchor | Any | None:
    """Получение информации о конкретном анкере

     Возвращает детальную конфигурацию анкера по его ID.

    Args:
        anchor_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Anchor | Any
    """

    return sync_detailed(
        anchor_id=anchor_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    anchor_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Anchor | Any]:
    """Получение информации о конкретном анкере

     Возвращает детальную конфигурацию анкера по его ID.

    Args:
        anchor_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Anchor | Any]
    """

    kwargs = _get_kwargs(
        anchor_id=anchor_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    anchor_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Anchor | Any | None:
    """Получение информации о конкретном анкере

     Возвращает детальную конфигурацию анкера по его ID.

    Args:
        anchor_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Anchor | Any
    """

    return (
        await asyncio_detailed(
            anchor_id=anchor_id,
            client=client,
        )
    ).parsed
