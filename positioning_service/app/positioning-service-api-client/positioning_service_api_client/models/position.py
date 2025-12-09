from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.single_measurement import SingleMeasurement


T = TypeVar("T", bound="Position")


@_attrs_define
class Position:
    """
    Attributes:
        tag_id (str):
        x (float): Координата X в метрах (в локальной системе координат предприятия).
        y (float): Координата Y в метрах.
        z (float): Координата Z в метрах (высота/этаж). Может быть 0 для 2D-систем.
        timestamp (datetime.datetime): Время вычисления координат.
        accuracy (float): Расчетная погрешность в метрах (например, на основе геометрии анкеров).
        source_measurements (list[SingleMeasurement] | Unset): Массив сырых измерений, использованных для расчета
            (включается, если запрошено).
    """

    tag_id: str
    x: float
    y: float
    z: float
    timestamp: datetime.datetime
    accuracy: float
    source_measurements: list[SingleMeasurement] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        tag_id = self.tag_id

        x = self.x

        y = self.y

        z = self.z

        timestamp = self.timestamp.isoformat()

        accuracy = self.accuracy

        source_measurements: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.source_measurements, Unset):
            source_measurements = []
            for source_measurements_item_data in self.source_measurements:
                source_measurements_item = source_measurements_item_data.to_dict()
                source_measurements.append(source_measurements_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tag_id": tag_id,
                "x": x,
                "y": y,
                "z": z,
                "timestamp": timestamp,
                "accuracy": accuracy,
            }
        )
        if source_measurements is not UNSET:
            field_dict["source_measurements"] = source_measurements

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.single_measurement import SingleMeasurement

        d = dict(src_dict)
        tag_id = d.pop("tag_id")

        x = d.pop("x")

        y = d.pop("y")

        z = d.pop("z")

        timestamp = isoparse(d.pop("timestamp"))

        accuracy = d.pop("accuracy")

        _source_measurements = d.pop("source_measurements", UNSET)
        source_measurements: list[SingleMeasurement] | Unset = UNSET
        if _source_measurements is not UNSET:
            source_measurements = []
            for source_measurements_item_data in _source_measurements:
                source_measurements_item = SingleMeasurement.from_dict(source_measurements_item_data)

                source_measurements.append(source_measurements_item)

        position = cls(
            tag_id=tag_id,
            x=x,
            y=y,
            z=z,
            timestamp=timestamp,
            accuracy=accuracy,
            source_measurements=source_measurements,
        )

        position.additional_properties = d
        return position

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
