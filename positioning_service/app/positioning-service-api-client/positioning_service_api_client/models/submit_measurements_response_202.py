from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SubmitMeasurementsResponse202")


@_attrs_define
class SubmitMeasurementsResponse202:
    """
    Attributes:
        message (str | Unset):  Example: Measurements accepted for processing.
        batch_id (UUID | Unset):  Example: 123e4567-e89b-12d3-a456-426614174000.
    """

    message: str | Unset = UNSET
    batch_id: UUID | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        message = self.message

        batch_id: str | Unset = UNSET
        if not isinstance(self.batch_id, Unset):
            batch_id = str(self.batch_id)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if message is not UNSET:
            field_dict["message"] = message
        if batch_id is not UNSET:
            field_dict["batch_id"] = batch_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        message = d.pop("message", UNSET)

        _batch_id = d.pop("batch_id", UNSET)
        batch_id: UUID | Unset
        if isinstance(_batch_id, Unset):
            batch_id = UNSET
        else:
            batch_id = UUID(_batch_id)

        submit_measurements_response_202 = cls(
            message=message,
            batch_id=batch_id,
        )

        submit_measurements_response_202.additional_properties = d
        return submit_measurements_response_202

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
