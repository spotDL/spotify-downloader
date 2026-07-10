from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.album_out import AlbumOut
    from ..models.artist_out import ArtistOut
    from ..models.playlist_out import PlaylistOut
    from ..models.track_out import TrackOut


T = TypeVar("T", bound="SearchResponse")


@_attrs_define
class SearchResponse:
    """``GET /search`` result: sectioned universal search + degraded sources.

    ``results`` is the ranked track list (kept as-is for existing clients);
    ``albums`` / ``artists`` / ``playlists`` are the other lightweight preview
    sections (each defaults empty). Every section carries preview views — the
    client resolves a ref for the full canonical graph.

        Attributes:
            degraded_sources (list[str]):
            results (list['TrackOut']):
            albums (Union[Unset, list['AlbumOut']]):
            artists (Union[Unset, list['ArtistOut']]):
            playlists (Union[Unset, list['PlaylistOut']]):
    """

    degraded_sources: list[str]
    results: list["TrackOut"]
    albums: Union[Unset, list["AlbumOut"]] = UNSET
    artists: Union[Unset, list["ArtistOut"]] = UNSET
    playlists: Union[Unset, list["PlaylistOut"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.album_out import AlbumOut
        from ..models.artist_out import ArtistOut
        from ..models.playlist_out import PlaylistOut
        from ..models.track_out import TrackOut

        degraded_sources = self.degraded_sources

        results = []
        for results_item_data in self.results:
            results_item = results_item_data.to_dict()
            results.append(results_item)

        albums: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.albums, Unset):
            albums = []
            for albums_item_data in self.albums:
                albums_item = albums_item_data.to_dict()
                albums.append(albums_item)

        artists: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.artists, Unset):
            artists = []
            for artists_item_data in self.artists:
                artists_item = artists_item_data.to_dict()
                artists.append(artists_item)

        playlists: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.playlists, Unset):
            playlists = []
            for playlists_item_data in self.playlists:
                playlists_item = playlists_item_data.to_dict()
                playlists.append(playlists_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "degraded_sources": degraded_sources,
                "results": results,
            }
        )
        if albums is not UNSET:
            field_dict["albums"] = albums
        if artists is not UNSET:
            field_dict["artists"] = artists
        if playlists is not UNSET:
            field_dict["playlists"] = playlists

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.album_out import AlbumOut
        from ..models.artist_out import ArtistOut
        from ..models.playlist_out import PlaylistOut
        from ..models.track_out import TrackOut

        d = dict(src_dict)
        degraded_sources = cast(list[str], d.pop("degraded_sources"))

        results = []
        _results = d.pop("results")
        for results_item_data in _results:
            results_item = TrackOut.from_dict(results_item_data)

            results.append(results_item)

        albums = []
        _albums = d.pop("albums", UNSET)
        for albums_item_data in _albums or []:
            albums_item = AlbumOut.from_dict(albums_item_data)

            albums.append(albums_item)

        artists = []
        _artists = d.pop("artists", UNSET)
        for artists_item_data in _artists or []:
            artists_item = ArtistOut.from_dict(artists_item_data)

            artists.append(artists_item)

        playlists = []
        _playlists = d.pop("playlists", UNSET)
        for playlists_item_data in _playlists or []:
            playlists_item = PlaylistOut.from_dict(playlists_item_data)

            playlists.append(playlists_item)

        search_response = cls(
            degraded_sources=degraded_sources,
            results=results,
            albums=albums,
            artists=artists,
            playlists=playlists,
        )

        search_response.additional_properties = d
        return search_response

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
