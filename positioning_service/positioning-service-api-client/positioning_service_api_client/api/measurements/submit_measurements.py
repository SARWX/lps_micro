from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.measurement_batch import MeasurementBatch
from ...models.submit_measurements_response_202 import SubmitMeasurementsResponse202
from ...models.validation_error import ValidationError
from ...types import Response


def _get_kwargs(
    *,
    body: MeasurementBatch,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/measurements",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | SubmitMeasurementsResponse202 | ValidationError | None:
    if response.status_code == 202:
        response_202 = SubmitMeasurementsResponse202.from_dict(response.json())

        return response_202

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 422:
        response_422 = ValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | SubmitMeasurementsResponse202 | ValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: MeasurementBatch,
) -> Response[Error | SubmitMeasurementsResponse202 | ValidationError]:
    """Прием пакета измерений от анкеров

     Основной endpoint для загрузки данных с базовых станций. Принимает массив измерений расстояний от
    анкеров до меток (tags). Сервис асинхронно обрабатывает их, вычисляет координаты методом
    трилатерации и обновляет кэш текущих позиций.

    Args:
        body (MeasurementBatch):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | SubmitMeasurementsResponse202 | ValidationError]
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
    client: AuthenticatedClient | Client,
    body: MeasurementBatch,
) -> Error | SubmitMeasurementsResponse202 | ValidationError | None:
    """Прием пакета измерений от анкеров

     Основной endpoint для загрузки данных с базовых станций. Принимает массив измерений расстояний от
    анкеров до меток (tags). Сервис асинхронно обрабатывает их, вычисляет координаты методом
    трилатерации и обновляет кэш текущих позиций.

    Args:
        body (MeasurementBatch):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | SubmitMeasurementsResponse202 | ValidationError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: MeasurementBatch,
) -> Response[Error | SubmitMeasurementsResponse202 | ValidationError]:
    """Прием пакета измерений от анкеров

     Основной endpoint для загрузки данных с базовых станций. Принимает массив измерений расстояний от
    анкеров до меток (tags). Сервис асинхронно обрабатывает их, вычисляет координаты методом
    трилатерации и обновляет кэш текущих позиций.

    Args:
        body (MeasurementBatch):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | SubmitMeasurementsResponse202 | ValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: MeasurementBatch,
) -> Error | SubmitMeasurementsResponse202 | ValidationError | None:
    """Прием пакета измерений от анкеров

     Основной endpoint для загрузки данных с базовых станций. Принимает массив измерений расстояний от
    анкеров до меток (tags). Сервис асинхронно обрабатывает их, вычисляет координаты методом
    трилатерации и обновляет кэш текущих позиций.

    Args:
        body (MeasurementBatch):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | SubmitMeasurementsResponse202 | ValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
