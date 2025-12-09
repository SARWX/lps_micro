from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.validation_error_details_item import ValidationErrorDetailsItem


T = TypeVar("T", bound="ValidationError")


@_attrs_define
class ValidationError:
    """
    Attributes:
        error_code (str | Unset):  Example: POSITION_NOT_FOUND.
        message (str | Unset):  Example: Position for tag 'tag-123' not found in cache or database..
        timestamp (datetime.datetime | Unset):
        details (list[ValidationErrorDetailsItem] | Unset):
    """

    error_code: str | Unset = UNSET
    message: str | Unset = UNSET
    timestamp: datetime.datetime | Unset = UNSET
    details: list[ValidationErrorDetailsItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        error_code = self.error_code

        message = self.message

        timestamp: str | Unset = UNSET
        if not isinstance(self.timestamp, Unset):
            timestamp = self.timestamp.isoformat()

        details: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.details, Unset):
            details = []
            for details_item_data in self.details:
                details_item = details_item_data.to_dict()
                details.append(details_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if error_code is not UNSET:
            field_dict["error_code"] = error_code
        if message is not UNSET:
            field_dict["message"] = message
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp
        if details is not UNSET:
            field_dict["details"] = details

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.validation_error_details_item import ValidationErrorDetailsItem

        d = dict(src_dict)
        error_code = d.pop("error_code", UNSET)

        message = d.pop("message", UNSET)

        _timestamp = d.pop("timestamp", UNSET)
        timestamp: datetime.datetime | Unset
        if isinstance(_timestamp, Unset):
            timestamp = UNSET
        else:
            timestamp = isoparse(_timestamp)

        _details = d.pop("details", UNSET)
        details: list[ValidationErrorDetailsItem] | Unset = UNSET
        if _details is not UNSET:
            details = []
            for details_item_data in _details:
                details_item = ValidationErrorDetailsItem.from_dict(details_item_data)

                details.append(details_item)

        validation_error = cls(
            error_code=error_code,
            message=message,
            timestamp=timestamp,
            details=details,
        )

        validation_error.additional_properties = d
        return validation_error

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
