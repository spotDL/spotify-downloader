from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.entity_envelope import EntityEnvelope


T = TypeVar("T", bound="ResolveResponse")


@_attrs_define
class ResolveResponse:
    """``POST /resolve`` result: the tagged entity + the sources that degraded.

    Attributes:
        degraded_sources (list[str]):
        entity (EntityEnvelope): A resolved entity tagged by ``type``; exactly one payload field is set.
    """

    degraded_sources: list[str]
    entity: "EntityEnvelope"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.entity_envelope import EntityEnvelope

        degraded_sources = self.degraded_sources

        entity = self.entity.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "degraded_sources": degraded_sources,
                "entity": entity,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.entity_envelope import EntityEnvelope

        d = dict(src_dict)
        degraded_sources = cast(list[str], d.pop("degraded_sources"))

        entity = EntityEnvelope.from_dict(d.pop("entity"))

        resolve_response = cls(
            degraded_sources=degraded_sources,
            entity=entity,
        )

        resolve_response.additional_properties = d
        return resolve_response

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
