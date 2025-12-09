import datetime
from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.position import Position
from ...types import UNSET, Response, Unset


def _get_kwargs(
    tag_id: str,
    *,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    limit: int | Unset = 1000,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_start_time = start_time.isoformat()
    params["start_time"] = json_start_time

    json_end_time = end_time.isoformat()
    params["end_time"] = json_end_time

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/positions/history/{tag_id}".format(
            tag_id=quote(str(tag_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | list[Position] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = Position.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | list[Position]]:
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
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    limit: int | Unset = 1000,
) -> Response[Error | list[Position]]:
    """Получение истории перемещений метки за период

     Возвращает массив записей о позициях метки за указанный временной интервал. Данные извлекаются из
    постоянного хранилища (БД).

    Args:
        tag_id (str):
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        limit (int | Unset):  Default: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[Position]]
    """

    kwargs = _get_kwargs(
        tag_id=tag_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    limit: int | Unset = 1000,
) -> Error | list[Position] | None:
    """Получение истории перемещений метки за период

     Возвращает массив записей о позициях метки за указанный временной интервал. Данные извлекаются из
    постоянного хранилища (БД).

    Args:
        tag_id (str):
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        limit (int | Unset):  Default: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[Position]
    """

    return sync_detailed(
        tag_id=tag_id,
        client=client,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    limit: int | Unset = 1000,
) -> Response[Error | list[Position]]:
    """Получение истории перемещений метки за период

     Возвращает массив записей о позициях метки за указанный временной интервал. Данные извлекаются из
    постоянного хранилища (БД).

    Args:
        tag_id (str):
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        limit (int | Unset):  Default: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[Position]]
    """

    kwargs = _get_kwargs(
        tag_id=tag_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tag_id: str,
    *,
    client: AuthenticatedClient | Client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    limit: int | Unset = 1000,
) -> Error | list[Position] | None:
    """Получение истории перемещений метки за период

     Возвращает массив записей о позициях метки за указанный временной интервал. Данные извлекаются из
    постоянного хранилища (БД).

    Args:
        tag_id (str):
        start_time (datetime.datetime):
        end_time (datetime.datetime):
        limit (int | Unset):  Default: 1000.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[Position]
    """

    return (
        await asyncio_detailed(
            tag_id=tag_id,
            client=client,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    ).parsed
