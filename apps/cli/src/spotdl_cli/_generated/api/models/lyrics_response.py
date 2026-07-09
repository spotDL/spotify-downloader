from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.lyrics_out import LyricsOut


T = TypeVar("T", bound="LyricsResponse")


@_attrs_define
class LyricsResponse:
    """``GET /tracks/{id}/lyrics``: the track id + its lyrics variants.

    Attributes:
        lyrics (list['LyricsOut']):
        track_id (str):
    """

    lyrics: list["LyricsOut"]
    track_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.lyrics_out import LyricsOut

        lyrics = []
        for lyrics_item_data in self.lyrics:
            lyrics_item = lyrics_item_data.to_dict()
            lyrics.append(lyrics_item)

        track_id = self.track_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "lyrics": lyrics,
                "track_id": track_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lyrics_out import LyricsOut

        d = dict(src_dict)
        lyrics = []
        _lyrics = d.pop("lyrics")
        for lyrics_item_data in _lyrics:
            lyrics_item = LyricsOut.from_dict(lyrics_item_data)

            lyrics.append(lyrics_item)

        track_id = d.pop("track_id")

        lyrics_response = cls(
            lyrics=lyrics,
            track_id=track_id,
        )

        lyrics_response.additional_properties = d
        return lyrics_response

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
