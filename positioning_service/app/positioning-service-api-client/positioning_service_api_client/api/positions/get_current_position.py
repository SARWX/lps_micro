from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.position import Position
from ...types import Response


def _get_kwargs(
    tag_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/positions/current/{tag_id}".format(
            tag_id=quote(str(tag_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | Position | None:
    if response.status_code == 200:
        response_200 = Position.from_dict(response.json())

        return response_200

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | Position]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | Position]:
    """Получение последней вычисленной позиции метки

     Возвращает последние известные координаты метки (сотрудника или объекта) из кэша сервиса.

    Args:
        tag_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | Position]
    """

    kwargs = _get_kwargs(
        tag_id=tag_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Error | Position | None:
    """Получение последней вычисленной позиции метки

     Возвращает последние известные координаты метки (сотрудника или объекта) из кэша сервиса.

    Args:
        tag_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | Position
    """

    return sync_detailed(
        tag_id=tag_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | Position]:
    """Получение последней вычисленной позиции метки

     Возвращает последние известные координаты метки (сотрудника или объекта) из кэша сервиса.

    Args:
        tag_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | Position]
    """

    kwargs = _get_kwargs(
        tag_id=tag_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Error | Position | None:
    """Получение последней вычисленной позиции метки

     Возвращает последние известные координаты метки (сотрудника или объекта) из кэша сервиса.

    Args:
        tag_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | Position
    """

    return (
        await asyncio_detailed(
            tag_id=tag_id,
            client=client,
        )
    ).parsed
