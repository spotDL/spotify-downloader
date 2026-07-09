from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreatePatRequest")


@_attrs_define
class CreatePatRequest:
    """Body of ``POST /auth/tokens``: mint a personal access token for the CLI.

    ``name`` is a required non-blank label (1–255 chars, matching the column
    width). ``expires_in_days`` is optional — when omitted the PAT never expires
    (``expires_at = NULL``); when given it must be a positive integer and the
    router converts it to an absolute ``expires_at`` via the shared clock.

        Attributes:
            name (str):
            expires_in_days (Union[None, Unset, int]):
    """

    name: str
    expires_in_days: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        expires_in_days: Union[None, Unset, int]
        if isinstance(self.expires_in_days, Unset):
            expires_in_days = UNSET
        else:
            expires_in_days = self.expires_in_days

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if expires_in_days is not UNSET:
            field_dict["expires_in_days"] = expires_in_days

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        def _parse_expires_in_days(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        expires_in_days = _parse_expires_in_days(d.pop("expires_in_days", UNSET))

        create_pat_request = cls(
            name=name,
            expires_in_days=expires_in_days,
        )

        create_pat_request.additional_properties = d
        return create_pat_request

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
