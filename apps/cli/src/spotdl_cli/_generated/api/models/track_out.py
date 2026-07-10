from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.album_ref_out import AlbumRefOut


T = TypeVar("T", bound="TrackOut")


@_attrs_define
class TrackOut:
    """A canonical track (metadata only; matches/lyrics are separate resources).

    Attributes:
        artists (list[str]):
        duration_ms (int):
        id (str):
        name (str):
        album (Union['AlbumRefOut', None, Unset]):
        copyright_text (Union[None, Unset, str]):
        cover_url (Union[None, Unset, str]):
        date (Union[None, Unset, str]):
        disc_number (Union[None, Unset, int]):
        explicit (Union[None, Unset, bool]):
        genres (Union[Unset, list[str]]):
        isrc (Union[None, Unset, str]):
        popularity (Union[None, Unset, int]):
        provider (Union[None, Unset, str]):
        provider_id (Union[None, Unset, str]):
        publisher (Union[None, Unset, str]):
        track_number (Union[None, Unset, int]):
        year (Union[None, Unset, int]):
    """

    artists: list[str]
    duration_ms: int
    id: str
    name: str
    album: Union["AlbumRefOut", None, Unset] = UNSET
    copyright_text: Union[None, Unset, str] = UNSET
    cover_url: Union[None, Unset, str] = UNSET
    date: Union[None, Unset, str] = UNSET
    disc_number: Union[None, Unset, int] = UNSET
    explicit: Union[None, Unset, bool] = UNSET
    genres: Union[Unset, list[str]] = UNSET
    isrc: Union[None, Unset, str] = UNSET
    popularity: Union[None, Unset, int] = UNSET
    provider: Union[None, Unset, str] = UNSET
    provider_id: Union[None, Unset, str] = UNSET
    publisher: Union[None, Unset, str] = UNSET
    track_number: Union[None, Unset, int] = UNSET
    year: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.album_ref_out import AlbumRefOut

        artists = self.artists

        duration_ms = self.duration_ms

        id = self.id

        name = self.name

        album: Union[None, Unset, dict[str, Any]]
        if isinstance(self.album, Unset):
            album = UNSET
        elif isinstance(self.album, AlbumRefOut):
            album = self.album.to_dict()
        else:
            album = self.album

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

        date: Union[None, Unset, str]
        if isinstance(self.date, Unset):
            date = UNSET
        else:
            date = self.date

        disc_number: Union[None, Unset, int]
        if isinstance(self.disc_number, Unset):
            disc_number = UNSET
        else:
            disc_number = self.disc_number

        explicit: Union[None, Unset, bool]
        if isinstance(self.explicit, Unset):
            explicit = UNSET
        else:
            explicit = self.explicit

        genres: Union[Unset, list[str]] = UNSET
        if not isinstance(self.genres, Unset):
            genres = self.genres

        isrc: Union[None, Unset, str]
        if isinstance(self.isrc, Unset):
            isrc = UNSET
        else:
            isrc = self.isrc

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

        publisher: Union[None, Unset, str]
        if isinstance(self.publisher, Unset):
            publisher = UNSET
        else:
            publisher = self.publisher

        track_number: Union[None, Unset, int]
        if isinstance(self.track_number, Unset):
            track_number = UNSET
        else:
            track_number = self.track_number

        year: Union[None, Unset, int]
        if isinstance(self.year, Unset):
            year = UNSET
        else:
            year = self.year

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "artists": artists,
                "duration_ms": duration_ms,
                "id": id,
                "name": name,
            }
        )
        if album is not UNSET:
            field_dict["album"] = album
        if copyright_text is not UNSET:
            field_dict["copyright_text"] = copyright_text
        if cover_url is not UNSET:
            field_dict["cover_url"] = cover_url
        if date is not UNSET:
            field_dict["date"] = date
        if disc_number is not UNSET:
            field_dict["disc_number"] = disc_number
        if explicit is not UNSET:
            field_dict["explicit"] = explicit
        if genres is not UNSET:
            field_dict["genres"] = genres
        if isrc is not UNSET:
            field_dict["isrc"] = isrc
        if popularity is not UNSET:
            field_dict["popularity"] = popularity
        if provider is not UNSET:
            field_dict["provider"] = provider
        if provider_id is not UNSET:
            field_dict["provider_id"] = provider_id
        if publisher is not UNSET:
            field_dict["publisher"] = publisher
        if track_number is not UNSET:
            field_dict["track_number"] = track_number
        if year is not UNSET:
            field_dict["year"] = year

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.album_ref_out import AlbumRefOut

        d = dict(src_dict)
        artists = cast(list[str], d.pop("artists"))

        duration_ms = d.pop("duration_ms")

        id = d.pop("id")

        name = d.pop("name")

        def _parse_album(data: object) -> Union["AlbumRefOut", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                album_type_0 = AlbumRefOut.from_dict(data)

                return album_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AlbumRefOut", None, Unset], data)

        album = _parse_album(d.pop("album", UNSET))

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

        def _parse_date(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        date = _parse_date(d.pop("date", UNSET))

        def _parse_disc_number(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        disc_number = _parse_disc_number(d.pop("disc_number", UNSET))

        def _parse_explicit(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        explicit = _parse_explicit(d.pop("explicit", UNSET))

        genres = cast(list[str], d.pop("genres", UNSET))

        def _parse_isrc(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        isrc = _parse_isrc(d.pop("isrc", UNSET))

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

        def _parse_publisher(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        publisher = _parse_publisher(d.pop("publisher", UNSET))

        def _parse_track_number(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        track_number = _parse_track_number(d.pop("track_number", UNSET))

        def _parse_year(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        year = _parse_year(d.pop("year", UNSET))

        track_out = cls(
            artists=artists,
            duration_ms=duration_ms,
            id=id,
            name=name,
            album=album,
            copyright_text=copyright_text,
            cover_url=cover_url,
            date=date,
            disc_number=disc_number,
            explicit=explicit,
            genres=genres,
            isrc=isrc,
            popularity=popularity,
            provider=provider,
            provider_id=provider_id,
            publisher=publisher,
            track_number=track_number,
            year=year,
        )

        track_out.additional_properties = d
        return track_out

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
