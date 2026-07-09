from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.match_out import MatchOut


T = TypeVar("T", bound="MatchesResponse")


@_attrs_define
class MatchesResponse:
    """``GET /tracks/{id}/matches``: the track id + its ranked matches.

    Attributes:
        matches (list['MatchOut']):
        track_id (str):
    """

    matches: list["MatchOut"]
    track_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.match_out import MatchOut

        matches = []
        for matches_item_data in self.matches:
            matches_item = matches_item_data.to_dict()
            matches.append(matches_item)

        track_id = self.track_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "matches": matches,
                "track_id": track_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.match_out import MatchOut

        d = dict(src_dict)
        matches = []
        _matches = d.pop("matches")
        for matches_item_data in _matches:
            matches_item = MatchOut.from_dict(matches_item_data)

            matches.append(matches_item)

        track_id = d.pop("track_id")

        matches_response = cls(
            matches=matches,
            track_id=track_id,
        )

        matches_response.additional_properties = d
        return matches_response

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
