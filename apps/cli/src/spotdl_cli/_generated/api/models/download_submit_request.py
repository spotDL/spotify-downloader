from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.output_format import OutputFormat
from ..models.overwrite_mode import OverwriteMode
from ..types import UNSET, Unset

T = TypeVar("T", bound="DownloadSubmitRequest")


@_attrs_define
class DownloadSubmitRequest:
    """Body of ``POST /downloads``: what and how to download.

    ``query`` is a URL, ``provider:type:id`` ref, or free text (a single track);
    an album/playlist URL is expanded server-side into N jobs. The ``None``
    engine fields fall back to the server's configured defaults at submit time.

        Attributes:
            query (str):
            bitrate (Union[None, Unset, str]):
            embed_lyrics (Union[Unset, bool]):  Default: True.
            generate_lrc (Union[Unset, bool]):  Default: False.
            generate_m3u (Union[Unset, bool]):  Default: False.
            generate_save_file (Union[Unset, bool]):  Default: False.
            m3u_template (Union[None, Unset, str]):
            output_format (Union[None, OutputFormat, Unset]):
            output_template (Union[None, Unset, str]):
            overwrite (Union[None, OverwriteMode, Unset]):
            sponsor_block (Union[Unset, bool]):  Default: False.
            update_archive (Union[Unset, bool]):  Default: False.
    """

    query: str
    bitrate: Union[None, Unset, str] = UNSET
    embed_lyrics: Union[Unset, bool] = True
    generate_lrc: Union[Unset, bool] = False
    generate_m3u: Union[Unset, bool] = False
    generate_save_file: Union[Unset, bool] = False
    m3u_template: Union[None, Unset, str] = UNSET
    output_format: Union[None, OutputFormat, Unset] = UNSET
    output_template: Union[None, Unset, str] = UNSET
    overwrite: Union[None, OverwriteMode, Unset] = UNSET
    sponsor_block: Union[Unset, bool] = False
    update_archive: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        bitrate: Union[None, Unset, str]
        if isinstance(self.bitrate, Unset):
            bitrate = UNSET
        else:
            bitrate = self.bitrate

        embed_lyrics = self.embed_lyrics

        generate_lrc = self.generate_lrc

        generate_m3u = self.generate_m3u

        generate_save_file = self.generate_save_file

        m3u_template: Union[None, Unset, str]
        if isinstance(self.m3u_template, Unset):
            m3u_template = UNSET
        else:
            m3u_template = self.m3u_template

        output_format: Union[None, Unset, str]
        if isinstance(self.output_format, Unset):
            output_format = UNSET
        elif isinstance(self.output_format, OutputFormat):
            output_format = self.output_format.value
        else:
            output_format = self.output_format

        output_template: Union[None, Unset, str]
        if isinstance(self.output_template, Unset):
            output_template = UNSET
        else:
            output_template = self.output_template

        overwrite: Union[None, Unset, str]
        if isinstance(self.overwrite, Unset):
            overwrite = UNSET
        elif isinstance(self.overwrite, OverwriteMode):
            overwrite = self.overwrite.value
        else:
            overwrite = self.overwrite

        sponsor_block = self.sponsor_block

        update_archive = self.update_archive

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if bitrate is not UNSET:
            field_dict["bitrate"] = bitrate
        if embed_lyrics is not UNSET:
            field_dict["embed_lyrics"] = embed_lyrics
        if generate_lrc is not UNSET:
            field_dict["generate_lrc"] = generate_lrc
        if generate_m3u is not UNSET:
            field_dict["generate_m3u"] = generate_m3u
        if generate_save_file is not UNSET:
            field_dict["generate_save_file"] = generate_save_file
        if m3u_template is not UNSET:
            field_dict["m3u_template"] = m3u_template
        if output_format is not UNSET:
            field_dict["output_format"] = output_format
        if output_template is not UNSET:
            field_dict["output_template"] = output_template
        if overwrite is not UNSET:
            field_dict["overwrite"] = overwrite
        if sponsor_block is not UNSET:
            field_dict["sponsor_block"] = sponsor_block
        if update_archive is not UNSET:
            field_dict["update_archive"] = update_archive

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        def _parse_bitrate(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        bitrate = _parse_bitrate(d.pop("bitrate", UNSET))

        embed_lyrics = d.pop("embed_lyrics", UNSET)

        generate_lrc = d.pop("generate_lrc", UNSET)

        generate_m3u = d.pop("generate_m3u", UNSET)

        generate_save_file = d.pop("generate_save_file", UNSET)

        def _parse_m3u_template(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        m3u_template = _parse_m3u_template(d.pop("m3u_template", UNSET))

        def _parse_output_format(data: object) -> Union[None, OutputFormat, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                output_format_type_0 = OutputFormat(data)

                return output_format_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, OutputFormat, Unset], data)

        output_format = _parse_output_format(d.pop("output_format", UNSET))

        def _parse_output_template(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        output_template = _parse_output_template(d.pop("output_template", UNSET))

        def _parse_overwrite(data: object) -> Union[None, OverwriteMode, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                overwrite_type_0 = OverwriteMode(data)

                return overwrite_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, OverwriteMode, Unset], data)

        overwrite = _parse_overwrite(d.pop("overwrite", UNSET))

        sponsor_block = d.pop("sponsor_block", UNSET)

        update_archive = d.pop("update_archive", UNSET)

        download_submit_request = cls(
            query=query,
            bitrate=bitrate,
            embed_lyrics=embed_lyrics,
            generate_lrc=generate_lrc,
            generate_m3u=generate_m3u,
            generate_save_file=generate_save_file,
            m3u_template=m3u_template,
            output_format=output_format,
            output_template=output_template,
            overwrite=overwrite,
            sponsor_block=sponsor_block,
            update_archive=update_archive,
        )

        download_submit_request.additional_properties = d
        return download_submit_request

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
