from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.entity_type import EntityType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.metadata_source_out import MetadataSourceOut


T = TypeVar("T", bound="SourcesResponse")


@_attrs_define
class SourcesResponse:
    """``GET /{tracks|albums|artists|playlists}/{id}/sources``: the entity's provenance.

    ``sources`` lists every provider snapshot linked to the canonical entity, ordered
    Spotify-first (``SOURCE_PRIORITY``), so the UI can show which providers contributed
    which fields to the merged row.

        Attributes:
            entity_id (str):
            entity_type (EntityType):
            sources (list['MetadataSourceOut']):
    """

    entity_id: str
    entity_type: EntityType
    sources: list["MetadataSourceOut"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.metadata_source_out import MetadataSourceOut

        entity_id = self.entity_id

        entity_type = self.entity_type.value

        sources = []
        for sources_item_data in self.sources:
            sources_item = sources_item_data.to_dict()
            sources.append(sources_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "sources": sources,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.metadata_source_out import MetadataSourceOut

        d = dict(src_dict)
        entity_id = d.pop("entity_id")

        entity_type = EntityType(d.pop("entity_type"))

        sources = []
        _sources = d.pop("sources")
        for sources_item_data in _sources:
            sources_item = MetadataSourceOut.from_dict(sources_item_data)

            sources.append(sources_item)

        sources_response = cls(
            entity_id=entity_id,
            entity_type=entity_type,
            sources=sources,
        )

        sources_response.additional_properties = d
        return sources_response

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
