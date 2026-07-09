from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="FeatureFlags")


@_attrs_define
class FeatureFlags:
    """The per-mode feature switches surfaced to clients (spec §4).

    Attributes:
        auth (bool):
        downloads (bool):
        library (bool):
        voting (bool):
    """

    auth: bool
    downloads: bool
    library: bool
    voting: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        auth = self.auth

        downloads = self.downloads

        library = self.library

        voting = self.voting

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "auth": auth,
                "downloads": downloads,
                "library": library,
                "voting": voting,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        auth = d.pop("auth")

        downloads = d.pop("downloads")

        library = d.pop("library")

        voting = d.pop("voting")

        feature_flags = cls(
            auth=auth,
            downloads=downloads,
            library=library,
            voting=voting,
        )

        feature_flags.additional_properties = d
        return feature_flags

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
