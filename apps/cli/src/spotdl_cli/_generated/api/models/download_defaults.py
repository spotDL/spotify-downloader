from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DownloadDefaults")


@_attrs_define
class DownloadDefaults:
    """The server's effective download configuration (``/config`` block).

    CONTRACT — read-only visibility so clients (web/TUI/Plan 8) pre-fill their
    submit forms and codegen against the server's operator defaults. Present only
    when :meth:`Settings.downloads_enabled` (``null`` in HOSTED).

        Attributes:
            add_unavailable (bool):
            bitrate (str):
            concurrency (int):
            create_skip_file (bool):
            detect_formats (list[str]):
            id3_separator (str):
            max_filename_length (Union[None, int]):
            output_format (str):
            output_template (str):
            playlist_numbering (bool):
            respect_skip_file (bool):
            restrict (str):
            retain_track_cover (bool):
            scan_existing (bool):
            skip_explicit (bool):
    """

    add_unavailable: bool
    bitrate: str
    concurrency: int
    create_skip_file: bool
    detect_formats: list[str]
    id3_separator: str
    max_filename_length: Union[None, int]
    output_format: str
    output_template: str
    playlist_numbering: bool
    respect_skip_file: bool
    restrict: str
    retain_track_cover: bool
    scan_existing: bool
    skip_explicit: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        add_unavailable = self.add_unavailable

        bitrate = self.bitrate

        concurrency = self.concurrency

        create_skip_file = self.create_skip_file

        detect_formats = self.detect_formats

        id3_separator = self.id3_separator

        max_filename_length: Union[None, int]
        max_filename_length = self.max_filename_length

        output_format = self.output_format

        output_template = self.output_template

        playlist_numbering = self.playlist_numbering

        respect_skip_file = self.respect_skip_file

        restrict = self.restrict

        retain_track_cover = self.retain_track_cover

        scan_existing = self.scan_existing

        skip_explicit = self.skip_explicit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "add_unavailable": add_unavailable,
                "bitrate": bitrate,
                "concurrency": concurrency,
                "create_skip_file": create_skip_file,
                "detect_formats": detect_formats,
                "id3_separator": id3_separator,
                "max_filename_length": max_filename_length,
                "output_format": output_format,
                "output_template": output_template,
                "playlist_numbering": playlist_numbering,
                "respect_skip_file": respect_skip_file,
                "restrict": restrict,
                "retain_track_cover": retain_track_cover,
                "scan_existing": scan_existing,
                "skip_explicit": skip_explicit,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        add_unavailable = d.pop("add_unavailable")

        bitrate = d.pop("bitrate")

        concurrency = d.pop("concurrency")

        create_skip_file = d.pop("create_skip_file")

        detect_formats = cast(list[str], d.pop("detect_formats"))

        id3_separator = d.pop("id3_separator")

        def _parse_max_filename_length(data: object) -> Union[None, int]:
            if data is None:
                return data
            return cast(Union[None, int], data)

        max_filename_length = _parse_max_filename_length(d.pop("max_filename_length"))

        output_format = d.pop("output_format")

        output_template = d.pop("output_template")

        playlist_numbering = d.pop("playlist_numbering")

        respect_skip_file = d.pop("respect_skip_file")

        restrict = d.pop("restrict")

        retain_track_cover = d.pop("retain_track_cover")

        scan_existing = d.pop("scan_existing")

        skip_explicit = d.pop("skip_explicit")

        download_defaults = cls(
            add_unavailable=add_unavailable,
            bitrate=bitrate,
            concurrency=concurrency,
            create_skip_file=create_skip_file,
            detect_formats=detect_formats,
            id3_separator=id3_separator,
            max_filename_length=max_filename_length,
            output_format=output_format,
            output_template=output_template,
            playlist_numbering=playlist_numbering,
            respect_skip_file=respect_skip_file,
            restrict=restrict,
            retain_track_cover=retain_track_cover,
            scan_existing=scan_existing,
            skip_explicit=skip_explicit,
        )

        download_defaults.additional_properties = d
        return download_defaults

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
