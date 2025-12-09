from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

if TYPE_CHECKING:
    from ..models.single_measurement import SingleMeasurement


T = TypeVar("T", bound="MeasurementBatch")


@_attrs_define
class MeasurementBatch:
    """
    Attributes:
        gateway_id (str): Идентификатор шлюза, отправившего пакет.
        timestamp (datetime.datetime): Время сбора измерений на шлюзе (ISO 8601).
        measurements (list[SingleMeasurement]): Массив измерений. Для трилатерации требуется минимум 3 измерения от
            разных анкеров.
    """

    gateway_id: str
    timestamp: datetime.datetime
    measurements: list[SingleMeasurement]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        gateway_id = self.gateway_id

        timestamp = self.timestamp.isoformat()

        measurements = []
        for measurements_item_data in self.measurements:
            measurements_item = measurements_item_data.to_dict()
            measurements.append(measurements_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "gateway_id": gateway_id,
                "timestamp": timestamp,
                "measurements": measurements,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.single_measurement import SingleMeasurement

        d = dict(src_dict)
        gateway_id = d.pop("gateway_id")

        timestamp = isoparse(d.pop("timestamp"))

        measurements = []
        _measurements = d.pop("measurements")
        for measurements_item_data in _measurements:
            measurements_item = SingleMeasurement.from_dict(measurements_item_data)

            measurements.append(measurements_item)

        measurement_batch = cls(
            gateway_id=gateway_id,
            timestamp=timestamp,
            measurements=measurements,
        )

        measurement_batch.additional_properties = d
        return measurement_batch

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
