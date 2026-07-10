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
        album_type (Union[None, Unset, str]):
        copyright_text (Union[None, Unset, str]):
        cover_url (Union[None, Unset, str]):
        genres (Union[Unset, list[str]]):
        label (Union[None, Unset, str]):
        popularity (Union[None, Unset, int]):
        provider (Union[None, Unset, str]):
        provider_id (Union[None, Unset, str]):
        track_count (Union[None, Unset, int]):
        tracks (Union[Unset, list['TrackOut']]):
        year (Union[None, Unset, int]):
    """

    id: str
    name: str
    album_artist: Union[None, Unset, str] = UNSET
    album_type: Union[None, Unset, str] = UNSET
    copyright_text: Union[None, Unset, str] = UNSET
    cover_url: Union[None, Unset, str] = UNSET
    genres: Union[Unset, list[str]] = UNSET
    label: Union[None, Unset, str] = UNSET
    popularity: Union[None, Unset, int] = UNSET
    provider: Union[None, Unset, str] = UNSET
    provider_id: Union[None, Unset, str] = UNSET
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

        album_type: Union[None, Unset, str]
        if isinstance(self.album_type, Unset):
            album_type = UNSET
        else:
            album_type = self.album_type

        copyright_text: Union[None, Unset, str]
        if isinstance(self.copyright_text, Unset):
            copyright_text = UNSET
        else:
            copyright_text = self.copyright_text

        cover_url: Union[None, Unset, str]
        if isinstance(self.cover_url, Unset):
            cover_url = UNSET
        else:
            cover_url = self.cover_url

        genres: Union[Unset, list[str]] = UNSET
        if not isinstance(self.genres, Unset):
            genres = self.genres

        label: Union[None, Unset, str]
        if isinstance(self.label, Unset):
            label = UNSET
        else:
            label = self.label

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
        if album_type is not UNSET:
            field_dict["album_type"] = album_type
        if copyright_text is not UNSET:
            field_dict["copyright_text"] = copyright_text
        if cover_url is not UNSET:
            field_dict["cover_url"] = cover_url
        if genres is not UNSET:
            field_dict["genres"] = genres
        if label is not UNSET:
            field_dict["label"] = label
        if popularity is not UNSET:
            field_dict["popularity"] = popularity
        if provider is not UNSET:
            field_dict["provider"] = provider
        if provider_id is not UNSET:
            field_dict["provider_id"] = provider_id
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

        def _parse_album_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        album_type = _parse_album_type(d.pop("album_type", UNSET))

        def _parse_copyright_text(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        copyright_text = _parse_copyright_text(d.pop("copyright_text", UNSET))

        def _parse_cover_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cover_url = _parse_cover_url(d.pop("cover_url", UNSET))

        genres = cast(list[str], d.pop("genres", UNSET))

        def _parse_label(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        label = _parse_label(d.pop("label", UNSET))

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
            album_type=album_type,
            copyright_text=copyright_text,
            cover_url=cover_url,
            genres=genres,
            label=label,
            popularity=popularity,
            provider=provider,
            provider_id=provider_id,
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
