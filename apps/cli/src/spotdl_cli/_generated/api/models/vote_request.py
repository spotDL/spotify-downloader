from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.vote_request_value import VoteRequestValue
from ..types import UNSET, Unset

T = TypeVar("T", bound="VoteRequest")


@_attrs_define
class VoteRequest:
    """Body of the vote endpoints: ``up`` (+1), ``down`` (-1), or ``retract``.

    A closed ``Literal`` so anything else is a 422 before the service runs — the
    only three verbs the state machine accepts.

        Attributes:
            value (VoteRequestValue):
    """

    value: VoteRequestValue
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = self.value.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        value = VoteRequestValue(d.pop("value"))

        vote_request = cls(
            value=value,
        )

        vote_request.additional_properties = d
        return vote_request

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
