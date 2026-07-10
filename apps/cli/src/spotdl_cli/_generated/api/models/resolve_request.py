from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResolveRequest")


@_attrs_define
class ResolveRequest:
    """Body of ``POST /resolve``: a URL, ``provider:type:id`` ref, or free text.

    ``force=True`` bypasses the snapshot cache and refetches from the providers,
    re-merging into the same canonical entity — the client "Refresh" affordance.

        Attributes:
            query (str):
            force (Union[Unset, bool]):  Default: False.
    """

    query: str
    force: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        force = self.force

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if force is not UNSET:
            field_dict["force"] = force

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        force = d.pop("force", UNSET)

        resolve_request = cls(
            query=query,
            force=force,
        )

        resolve_request.additional_properties = d
        return resolve_request

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
