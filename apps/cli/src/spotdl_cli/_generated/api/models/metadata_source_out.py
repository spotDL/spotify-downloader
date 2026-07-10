import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.entity_type import EntityType
from ..models.provider_id import ProviderId
from ..types import UNSET, Unset

T = TypeVar("T", bound="MetadataSourceOut")


@_attrs_define
class MetadataSourceOut:
    """One provider's contribution to a canonical entity (``.../{id}/sources`` element).

    The merged canonical row still displays Spotify-first; this is the per-source
    provenance the "Metadata Sources" panel renders. Only the fields relevant to the
    entity type are populated (``followers`` for an artist, ``label``/``year`` for an
    album, ``isrc`` for a track, …); the rest stay ``null``/empty.

        Attributes:
            entity_type (EntityType):
            fetched_at (datetime.datetime):
            provider (ProviderId):
            provider_entity_id (str):
            album_name (Union[None, Unset, str]):
            artist_names (Union[Unset, list[str]]):
            cover_url (Union[None, Unset, str]):
            followers (Union[None, Unset, int]):
            genres (Union[Unset, list[str]]):
            isrc (Union[None, Unset, str]):
            label (Union[None, Unset, str]):
            listeners (Union[None, Unset, int]):
            name (Union[None, Unset, str]):
            playcount (Union[None, Unset, int]):
            popularity (Union[None, Unset, int]):
            year (Union[None, Unset, int]):
    """

    entity_type: EntityType
    fetched_at: datetime.datetime
    provider: ProviderId
    provider_entity_id: str
    album_name: Union[None, Unset, str] = UNSET
    artist_names: Union[Unset, list[str]] = UNSET
    cover_url: Union[None, Unset, str] = UNSET
    followers: Union[None, Unset, int] = UNSET
    genres: Union[Unset, list[str]] = UNSET
    isrc: Union[None, Unset, str] = UNSET
    label: Union[None, Unset, str] = UNSET
    listeners: Union[None, Unset, int] = UNSET
    name: Union[None, Unset, str] = UNSET
    playcount: Union[None, Unset, int] = UNSET
    popularity: Union[None, Unset, int] = UNSET
    year: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        entity_type = self.entity_type.value

        fetched_at = self.fetched_at.isoformat()

        provider = self.provider.value

        provider_entity_id = self.provider_entity_id

        album_name: Union[None, Unset, str]
        if isinstance(self.album_name, Unset):
            album_name = UNSET
        else:
            album_name = self.album_name

        artist_names: Union[Unset, list[str]] = UNSET
        if not isinstance(self.artist_names, Unset):
            artist_names = self.artist_names

        cover_url: Union[None, Unset, str]
        if isinstance(self.cover_url, Unset):
            cover_url = UNSET
        else:
            cover_url = self.cover_url

        followers: Union[None, Unset, int]
        if isinstance(self.followers, Unset):
            followers = UNSET
        else:
            followers = self.followers

        genres: Union[Unset, list[str]] = UNSET
        if not isinstance(self.genres, Unset):
            genres = self.genres

        isrc: Union[None, Unset, str]
        if isinstance(self.isrc, Unset):
            isrc = UNSET
        else:
            isrc = self.isrc

        label: Union[None, Unset, str]
        if isinstance(self.label, Unset):
            label = UNSET
        else:
            label = self.label

        listeners: Union[None, Unset, int]
        if isinstance(self.listeners, Unset):
            listeners = UNSET
        else:
            listeners = self.listeners

        name: Union[None, Unset, str]
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        playcount: Union[None, Unset, int]
        if isinstance(self.playcount, Unset):
            playcount = UNSET
        else:
            playcount = self.playcount

        popularity: Union[None, Unset, int]
        if isinstance(self.popularity, Unset):
            popularity = UNSET
        else:
            popularity = self.popularity

        year: Union[None, Unset, int]
        if isinstance(self.year, Unset):
            year = UNSET
        else:
            year = self.year

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "entity_type": entity_type,
                "fetched_at": fetched_at,
                "provider": provider,
                "provider_entity_id": provider_entity_id,
            }
        )
        if album_name is not UNSET:
            field_dict["album_name"] = album_name
        if artist_names is not UNSET:
            field_dict["artist_names"] = artist_names
        if cover_url is not UNSET:
            field_dict["cover_url"] = cover_url
        if followers is not UNSET:
            field_dict["followers"] = followers
        if genres is not UNSET:
            field_dict["genres"] = genres
        if isrc is not UNSET:
            field_dict["isrc"] = isrc
        if label is not UNSET:
            field_dict["label"] = label
        if listeners is not UNSET:
            field_dict["listeners"] = listeners
        if name is not UNSET:
            field_dict["name"] = name
        if playcount is not UNSET:
            field_dict["playcount"] = playcount
        if popularity is not UNSET:
            field_dict["popularity"] = popularity
        if year is not UNSET:
            field_dict["year"] = year

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        entity_type = EntityType(d.pop("entity_type"))

        fetched_at = isoparse(d.pop("fetched_at"))

        provider = ProviderId(d.pop("provider"))

        provider_entity_id = d.pop("provider_entity_id")

        def _parse_album_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        album_name = _parse_album_name(d.pop("album_name", UNSET))

        artist_names = cast(list[str], d.pop("artist_names", UNSET))

        def _parse_cover_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cover_url = _parse_cover_url(d.pop("cover_url", UNSET))

        def _parse_followers(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        followers = _parse_followers(d.pop("followers", UNSET))

        genres = cast(list[str], d.pop("genres", UNSET))

        def _parse_isrc(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        isrc = _parse_isrc(d.pop("isrc", UNSET))

        def _parse_label(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        label = _parse_label(d.pop("label", UNSET))

        def _parse_listeners(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        listeners = _parse_listeners(d.pop("listeners", UNSET))

        def _parse_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_playcount(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        playcount = _parse_playcount(d.pop("playcount", UNSET))

        def _parse_popularity(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        popularity = _parse_popularity(d.pop("popularity", UNSET))

        def _parse_year(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        year = _parse_year(d.pop("year", UNSET))

        metadata_source_out = cls(
            entity_type=entity_type,
            fetched_at=fetched_at,
            provider=provider,
            provider_entity_id=provider_entity_id,
            album_name=album_name,
            artist_names=artist_names,
            cover_url=cover_url,
            followers=followers,
            genres=genres,
            isrc=isrc,
            label=label,
            listeners=listeners,
            name=name,
            playcount=playcount,
            popularity=popularity,
            year=year,
        )

        metadata_source_out.additional_properties = d
        return metadata_source_out

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
