from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.track_out import TrackOut


T = TypeVar("T", bound="ArtistOut")


@_attrs_define
class ArtistOut:
    """A canonical artist with its (metadata-only) top tracks.

    Attributes:
        id (str):
        name (str):
        genres (Union[Unset, list[str]]):
        image_url (Union[None, Unset, str]):
        tracks (Union[Unset, list['TrackOut']]):
    """

    id: str
    name: str
    genres: Union[Unset, list[str]] = UNSET
    image_url: Union[None, Unset, str] = UNSET
    tracks: Union[Unset, list["TrackOut"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.track_out import TrackOut

        id = self.id

        name = self.name

        genres: Union[Unset, list[str]] = UNSET
        if not isinstance(self.genres, Unset):
            genres = self.genres

        image_url: Union[None, Unset, str]
        if isinstance(self.image_url, Unset):
            image_url = UNSET
        else:
            image_url = self.image_url

        tracks: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.tracks, Unset):
            tracks = []
            for tracks_item_data in self.tracks:
                tracks_item = tracks_item_data.to_dict()
                tracks.append(tracks_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
            }
        )
        if genres is not UNSET:
            field_dict["genres"] = genres
        if image_url is not UNSET:
            field_dict["image_url"] = image_url
        if tracks is not UNSET:
            field_dict["tracks"] = tracks

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.track_out import TrackOut

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        genres = cast(list[str], d.pop("genres", UNSET))

        def _parse_image_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        image_url = _parse_image_url(d.pop("image_url", UNSET))

        tracks = []
        _tracks = d.pop("tracks", UNSET)
        for tracks_item_data in _tracks or []:
            tracks_item = TrackOut.from_dict(tracks_item_data)

            tracks.append(tracks_item)

        artist_out = cls(
            id=id,
            name=name,
            genres=genres,
            image_url=image_url,
            tracks=tracks,
        )

        artist_out.additional_properties = d
        return artist_out

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
