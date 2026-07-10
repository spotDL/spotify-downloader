from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.track_out import TrackOut


T = TypeVar("T", bound="PlaylistOut")


@_attrs_define
class PlaylistOut:
    """A canonical playlist with its ordered (metadata-only) track listing.

    Attributes:
        id (str):
        name (str):
        cover_url (Union[None, Unset, str]):
        description (Union[None, Unset, str]):
        owner (Union[None, Unset, str]):
        provider (Union[None, Unset, str]):
        provider_id (Union[None, Unset, str]):
        tracks (Union[Unset, list['TrackOut']]):
    """

    id: str
    name: str
    cover_url: Union[None, Unset, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    owner: Union[None, Unset, str] = UNSET
    provider: Union[None, Unset, str] = UNSET
    provider_id: Union[None, Unset, str] = UNSET
    tracks: Union[Unset, list["TrackOut"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.track_out import TrackOut

        id = self.id

        name = self.name

        cover_url: Union[None, Unset, str]
        if isinstance(self.cover_url, Unset):
            cover_url = UNSET
        else:
            cover_url = self.cover_url

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        owner: Union[None, Unset, str]
        if isinstance(self.owner, Unset):
            owner = UNSET
        else:
            owner = self.owner

        provider: Union[None, Unset, str]
        if isinstance(self.provider, Unset):
            provider = UNSET
        else:
            provider = self.provider

        provider_id: Union[None, Unset, str]
        if isinstance(self.provider_id, Unset):
            provider_id = UNSET
        else:
            provider_id = self.provider_id

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
        if cover_url is not UNSET:
            field_dict["cover_url"] = cover_url
        if description is not UNSET:
            field_dict["description"] = description
        if owner is not UNSET:
            field_dict["owner"] = owner
        if provider is not UNSET:
            field_dict["provider"] = provider
        if provider_id is not UNSET:
            field_dict["provider_id"] = provider_id
        if tracks is not UNSET:
            field_dict["tracks"] = tracks

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.track_out import TrackOut

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        def _parse_cover_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cover_url = _parse_cover_url(d.pop("cover_url", UNSET))

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_owner(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        owner = _parse_owner(d.pop("owner", UNSET))

        def _parse_provider(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        provider = _parse_provider(d.pop("provider", UNSET))

        def _parse_provider_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        provider_id = _parse_provider_id(d.pop("provider_id", UNSET))

        tracks = []
        _tracks = d.pop("tracks", UNSET)
        for tracks_item_data in _tracks or []:
            tracks_item = TrackOut.from_dict(tracks_item_data)

            tracks.append(tracks_item)

        playlist_out = cls(
            id=id,
            name=name,
            cover_url=cover_url,
            description=description,
            owner=owner,
            provider=provider,
            provider_id=provider_id,
            tracks=tracks,
        )

        playlist_out.additional_properties = d
        return playlist_out

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
