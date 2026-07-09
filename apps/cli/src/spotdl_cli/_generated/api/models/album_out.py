from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.track_out import TrackOut


T = TypeVar("T", bound="AlbumOut")


@_attrs_define
class AlbumOut:
    """A canonical album with its (metadata-only) track listing.

    Attributes:
        id (str):
        name (str):
        album_artist (Union[None, Unset, str]):
        cover_url (Union[None, Unset, str]):
        track_count (Union[None, Unset, int]):
        tracks (Union[Unset, list['TrackOut']]):
        year (Union[None, Unset, int]):
    """

    id: str
    name: str
    album_artist: Union[None, Unset, str] = UNSET
    cover_url: Union[None, Unset, str] = UNSET
    track_count: Union[None, Unset, int] = UNSET
    tracks: Union[Unset, list["TrackOut"]] = UNSET
    year: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.track_out import TrackOut

        id = self.id

        name = self.name

        album_artist: Union[None, Unset, str]
        if isinstance(self.album_artist, Unset):
            album_artist = UNSET
        else:
            album_artist = self.album_artist

        cover_url: Union[None, Unset, str]
        if isinstance(self.cover_url, Unset):
            cover_url = UNSET
        else:
            cover_url = self.cover_url

        track_count: Union[None, Unset, int]
        if isinstance(self.track_count, Unset):
            track_count = UNSET
        else:
            track_count = self.track_count

        tracks: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.tracks, Unset):
            tracks = []
            for tracks_item_data in self.tracks:
                tracks_item = tracks_item_data.to_dict()
                tracks.append(tracks_item)

        year: Union[None, Unset, int]
        if isinstance(self.year, Unset):
            year = UNSET
        else:
            year = self.year

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
            }
        )
        if album_artist is not UNSET:
            field_dict["album_artist"] = album_artist
        if cover_url is not UNSET:
            field_dict["cover_url"] = cover_url
        if track_count is not UNSET:
            field_dict["track_count"] = track_count
        if tracks is not UNSET:
            field_dict["tracks"] = tracks
        if year is not UNSET:
            field_dict["year"] = year

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.track_out import TrackOut

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        def _parse_album_artist(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        album_artist = _parse_album_artist(d.pop("album_artist", UNSET))

        def _parse_cover_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cover_url = _parse_cover_url(d.pop("cover_url", UNSET))

        def _parse_track_count(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        track_count = _parse_track_count(d.pop("track_count", UNSET))

        tracks = []
        _tracks = d.pop("tracks", UNSET)
        for tracks_item_data in _tracks or []:
            tracks_item = TrackOut.from_dict(tracks_item_data)

            tracks.append(tracks_item)

        def _parse_year(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        year = _parse_year(d.pop("year", UNSET))

        album_out = cls(
            id=id,
            name=name,
            album_artist=album_artist,
            cover_url=cover_url,
            track_count=track_count,
            tracks=tracks,
            year=year,
        )

        album_out.additional_properties = d
        return album_out

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
