from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.entity_type import EntityType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.album_out import AlbumOut
    from ..models.artist_out import ArtistOut
    from ..models.playlist_out import PlaylistOut
    from ..models.track_out import TrackOut


T = TypeVar("T", bound="EntityEnvelope")


@_attrs_define
class EntityEnvelope:
    """A resolved entity tagged by ``type``; exactly one payload field is set.

    Attributes:
        type_ (EntityType):
        album (Union['AlbumOut', None, Unset]):
        artist (Union['ArtistOut', None, Unset]):
        playlist (Union['PlaylistOut', None, Unset]):
        track (Union['TrackOut', None, Unset]):
    """

    type_: EntityType
    album: Union["AlbumOut", None, Unset] = UNSET
    artist: Union["ArtistOut", None, Unset] = UNSET
    playlist: Union["PlaylistOut", None, Unset] = UNSET
    track: Union["TrackOut", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.album_out import AlbumOut
        from ..models.artist_out import ArtistOut
        from ..models.playlist_out import PlaylistOut
        from ..models.track_out import TrackOut

        type_ = self.type_.value

        album: Union[None, Unset, dict[str, Any]]
        if isinstance(self.album, Unset):
            album = UNSET
        elif isinstance(self.album, AlbumOut):
            album = self.album.to_dict()
        else:
            album = self.album

        artist: Union[None, Unset, dict[str, Any]]
        if isinstance(self.artist, Unset):
            artist = UNSET
        elif isinstance(self.artist, ArtistOut):
            artist = self.artist.to_dict()
        else:
            artist = self.artist

        playlist: Union[None, Unset, dict[str, Any]]
        if isinstance(self.playlist, Unset):
            playlist = UNSET
        elif isinstance(self.playlist, PlaylistOut):
            playlist = self.playlist.to_dict()
        else:
            playlist = self.playlist

        track: Union[None, Unset, dict[str, Any]]
        if isinstance(self.track, Unset):
            track = UNSET
        elif isinstance(self.track, TrackOut):
            track = self.track.to_dict()
        else:
            track = self.track

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if album is not UNSET:
            field_dict["album"] = album
        if artist is not UNSET:
            field_dict["artist"] = artist
        if playlist is not UNSET:
            field_dict["playlist"] = playlist
        if track is not UNSET:
            field_dict["track"] = track

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.album_out import AlbumOut
        from ..models.artist_out import ArtistOut
        from ..models.playlist_out import PlaylistOut
        from ..models.track_out import TrackOut

        d = dict(src_dict)
        type_ = EntityType(d.pop("type"))

        def _parse_album(data: object) -> Union["AlbumOut", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                album_type_0 = AlbumOut.from_dict(data)

                return album_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AlbumOut", None, Unset], data)

        album = _parse_album(d.pop("album", UNSET))

        def _parse_artist(data: object) -> Union["ArtistOut", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                artist_type_0 = ArtistOut.from_dict(data)

                return artist_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ArtistOut", None, Unset], data)

        artist = _parse_artist(d.pop("artist", UNSET))

        def _parse_playlist(data: object) -> Union["PlaylistOut", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                playlist_type_0 = PlaylistOut.from_dict(data)

                return playlist_type_0
            except:  # noqa: E722
                pass
            return cast(Union["PlaylistOut", None, Unset], data)

        playlist = _parse_playlist(d.pop("playlist", UNSET))

        def _parse_track(data: object) -> Union["TrackOut", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                track_type_0 = TrackOut.from_dict(data)

                return track_type_0
            except:  # noqa: E722
                pass
            return cast(Union["TrackOut", None, Unset], data)

        track = _parse_track(d.pop("track", UNSET))

        entity_envelope = cls(
            type_=type_,
            album=album,
            artist=artist,
            playlist=playlist,
            track=track,
        )

        entity_envelope.additional_properties = d
        return entity_envelope

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
