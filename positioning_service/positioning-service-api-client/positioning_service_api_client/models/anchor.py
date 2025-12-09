from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="Anchor")


@_attrs_define
class Anchor:
    """
    Attributes:
        anchor_id (str): Уникальный аппаратный или логический идентификатор анкера.
        x (float): Фиксированная координата X анкера в системе.
        y (float):
        z (float):
        is_active (bool): Флаг, указывающий, используется ли анкер в данный момент для вычислений.
        description (str | Unset): Человеко-читаемое описание местоположения (например, "Цех №1, Северная стена").
        last_calibration (datetime.datetime | Unset): Дата последней калибровки.
    """

    anchor_id: str
    x: float
    y: float
    z: float
    is_active: bool
    description: str | Unset = UNSET
    last_calibration: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        anchor_id = self.anchor_id

        x = self.x

        y = self.y

        z = self.z

        is_active = self.is_active

        description = self.description

        last_calibration: str | Unset = UNSET
        if not isinstance(self.last_calibration, Unset):
            last_calibration = self.last_calibration.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "anchor_id": anchor_id,
                "x": x,
                "y": y,
                "z": z,
                "is_active": is_active,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if last_calibration is not UNSET:
            field_dict["last_calibration"] = last_calibration

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        anchor_id = d.pop("anchor_id")

        x = d.pop("x")

        y = d.pop("y")

        z = d.pop("z")

        is_active = d.pop("is_active")

        description = d.pop("description", UNSET)

        _last_calibration = d.pop("last_calibration", UNSET)
        last_calibration: datetime.datetime | Unset
        if isinstance(_last_calibration, Unset):
            last_calibration = UNSET
        else:
            last_calibration = isoparse(_last_calibration)

        anchor = cls(
            anchor_id=anchor_id,
            x=x,
            y=y,
            z=z,
            is_active=is_active,
            description=description,
            last_calibration=last_calibration,
        )

        anchor.additional_properties = d
        return anchor

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
