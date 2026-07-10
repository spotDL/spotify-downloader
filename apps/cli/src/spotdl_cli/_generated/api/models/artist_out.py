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
        bio (Union[None, Unset, str]):
        country (Union[None, Unset, str]):
        followers (Union[None, Unset, int]):
        genres (Union[Unset, list[str]]):
        header_url (Union[None, Unset, str]):
        image_url (Union[None, Unset, str]):
        popularity (Union[None, Unset, int]):
        provider (Union[None, Unset, str]):
        provider_id (Union[None, Unset, str]):
        tracks (Union[Unset, list['TrackOut']]):
    """

    id: str
    name: str
    bio: Union[None, Unset, str] = UNSET
    country: Union[None, Unset, str] = UNSET
    followers: Union[None, Unset, int] = UNSET
    genres: Union[Unset, list[str]] = UNSET
    header_url: Union[None, Unset, str] = UNSET
    image_url: Union[None, Unset, str] = UNSET
    popularity: Union[None, Unset, int] = UNSET
    provider: Union[None, Unset, str] = UNSET
    provider_id: Union[None, Unset, str] = UNSET
    tracks: Union[Unset, list["TrackOut"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.track_out import TrackOut

        id = self.id

        name = self.name

        bio: Union[None, Unset, str]
        if isinstance(self.bio, Unset):
            bio = UNSET
        else:
            bio = self.bio

        country: Union[None, Unset, str]
        if isinstance(self.country, Unset):
            country = UNSET
        else:
            country = self.country

        followers: Union[None, Unset, int]
        if isinstance(self.followers, Unset):
            followers = UNSET
        else:
            followers = self.followers

        genres: Union[Unset, list[str]] = UNSET
        if not isinstance(self.genres, Unset):
            genres = self.genres

        header_url: Union[None, Unset, str]
        if isinstance(self.header_url, Unset):
            header_url = UNSET
        else:
            header_url = self.header_url

        image_url: Union[None, Unset, str]
        if isinstance(self.image_url, Unset):
            image_url = UNSET
        else:
            image_url = self.image_url

        popularity: Union[None, Unset, int]
        if isinstance(self.popularity, Unset):
            popularity = UNSET
        else:
            popularity = self.popularity

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
        if bio is not UNSET:
            field_dict["bio"] = bio
        if country is not UNSET:
            field_dict["country"] = country
        if followers is not UNSET:
            field_dict["followers"] = followers
        if genres is not UNSET:
            field_dict["genres"] = genres
        if header_url is not UNSET:
            field_dict["header_url"] = header_url
        if image_url is not UNSET:
            field_dict["image_url"] = image_url
        if popularity is not UNSET:
            field_dict["popularity"] = popularity
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

        def _parse_bio(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        bio = _parse_bio(d.pop("bio", UNSET))

        def _parse_country(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        country = _parse_country(d.pop("country", UNSET))

        def _parse_followers(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        followers = _parse_followers(d.pop("followers", UNSET))

        genres = cast(list[str], d.pop("genres", UNSET))

        def _parse_header_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        header_url = _parse_header_url(d.pop("header_url", UNSET))

        def _parse_image_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        image_url = _parse_image_url(d.pop("image_url", UNSET))

        def _parse_popularity(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        popularity = _parse_popularity(d.pop("popularity", UNSET))

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

        artist_out = cls(
            id=id,
            name=name,
            bio=bio,
            country=country,
            followers=followers,
            genres=genres,
            header_url=header_url,
            image_url=image_url,
            popularity=popularity,
            provider=provider,
            provider_id=provider_id,
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
