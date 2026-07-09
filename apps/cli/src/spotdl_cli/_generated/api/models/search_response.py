from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.track_out import TrackOut


T = TypeVar("T", bound="SearchResponse")


@_attrs_define
class SearchResponse:
    """``GET /search`` result: a ranked track list + degraded sources.

    Attributes:
        degraded_sources (list[str]):
        results (list['TrackOut']):
    """

    degraded_sources: list[str]
    results: list["TrackOut"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.track_out import TrackOut

        degraded_sources = self.degraded_sources

        results = []
        for results_item_data in self.results:
            results_item = results_item_data.to_dict()
            results.append(results_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "degraded_sources": degraded_sources,
                "results": results,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.track_out import TrackOut

        d = dict(src_dict)
        degraded_sources = cast(list[str], d.pop("degraded_sources"))

        results = []
        _results = d.pop("results")
        for results_item_data in _results:
            results_item = TrackOut.from_dict(results_item_data)

            results.append(results_item)

        search_response = cls(
            degraded_sources=degraded_sources,
            results=results,
        )

        search_response.additional_properties = d
        return search_response

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
