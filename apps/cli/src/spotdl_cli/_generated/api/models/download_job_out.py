import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.batch_kind import BatchKind
from ..models.download_status import DownloadStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="DownloadJobOut")


@_attrs_define
class DownloadJobOut:
    """One download job (queue row) as returned across the download surface.

    Attributes:
        artists (list[str]):
        batch_id (Union[None, UUID]):
        batch_kind (Union[BatchKind, None]):
        batch_name (Union[None, str]):
        bitrate (Union[None, str]):
        cover_url (Union[None, str]):
        created_at (datetime.datetime):
        error_message (Union[None, str]):
        error_step (Union[None, str]):
        finished_at (Union[None, datetime.datetime]):
        id (UUID):
        list_position (Union[None, int]):
        output_format (Union[None, str]):
        output_path (Union[None, str]):
        output_template (Union[None, str]):
        progress (float):
        skip_reason (Union[None, str]):
        started_at (Union[None, datetime.datetime]):
        status (DownloadStatus): Lifecycle state of a ``download_jobs`` row (Plan 7 queue).
        track_id (Union[None, UUID]):
        track_name (Union[None, str]):
    """

    artists: list[str]
    batch_id: Union[None, UUID]
    batch_kind: Union[BatchKind, None]
    batch_name: Union[None, str]
    bitrate: Union[None, str]
    cover_url: Union[None, str]
    created_at: datetime.datetime
    error_message: Union[None, str]
    error_step: Union[None, str]
    finished_at: Union[None, datetime.datetime]
    id: UUID
    list_position: Union[None, int]
    output_format: Union[None, str]
    output_path: Union[None, str]
    output_template: Union[None, str]
    progress: float
    skip_reason: Union[None, str]
    started_at: Union[None, datetime.datetime]
    status: DownloadStatus
    track_id: Union[None, UUID]
    track_name: Union[None, str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        artists = self.artists

        batch_id: Union[None, str]
        if isinstance(self.batch_id, UUID):
            batch_id = str(self.batch_id)
        else:
            batch_id = self.batch_id

        batch_kind: Union[None, str]
        if isinstance(self.batch_kind, BatchKind):
            batch_kind = self.batch_kind.value
        else:
            batch_kind = self.batch_kind

        batch_name: Union[None, str]
        batch_name = self.batch_name

        bitrate: Union[None, str]
        bitrate = self.bitrate

        cover_url: Union[None, str]
        cover_url = self.cover_url

        created_at = self.created_at.isoformat()

        error_message: Union[None, str]
        error_message = self.error_message

        error_step: Union[None, str]
        error_step = self.error_step

        finished_at: Union[None, str]
        if isinstance(self.finished_at, datetime.datetime):
            finished_at = self.finished_at.isoformat()
        else:
            finished_at = self.finished_at

        id = str(self.id)

        list_position: Union[None, int]
        list_position = self.list_position

        output_format: Union[None, str]
        output_format = self.output_format

        output_path: Union[None, str]
        output_path = self.output_path

        output_template: Union[None, str]
        output_template = self.output_template

        progress = self.progress

        skip_reason: Union[None, str]
        skip_reason = self.skip_reason

        started_at: Union[None, str]
        if isinstance(self.started_at, datetime.datetime):
            started_at = self.started_at.isoformat()
        else:
            started_at = self.started_at

        status = self.status.value

        track_id: Union[None, str]
        if isinstance(self.track_id, UUID):
            track_id = str(self.track_id)
        else:
            track_id = self.track_id

        track_name: Union[None, str]
        track_name = self.track_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "artists": artists,
                "batch_id": batch_id,
                "batch_kind": batch_kind,
                "batch_name": batch_name,
                "bitrate": bitrate,
                "cover_url": cover_url,
                "created_at": created_at,
                "error_message": error_message,
                "error_step": error_step,
                "finished_at": finished_at,
                "id": id,
                "list_position": list_position,
                "output_format": output_format,
                "output_path": output_path,
                "output_template": output_template,
                "progress": progress,
                "skip_reason": skip_reason,
                "started_at": started_at,
                "status": status,
                "track_id": track_id,
                "track_name": track_name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        artists = cast(list[str], d.pop("artists"))

        def _parse_batch_id(data: object) -> Union[None, UUID]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                batch_id_type_0 = UUID(data)

                return batch_id_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, UUID], data)

        batch_id = _parse_batch_id(d.pop("batch_id"))

        def _parse_batch_kind(data: object) -> Union[BatchKind, None]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                batch_kind_type_0 = BatchKind(data)

                return batch_kind_type_0
            except:  # noqa: E722
                pass
            return cast(Union[BatchKind, None], data)

        batch_kind = _parse_batch_kind(d.pop("batch_kind"))

        def _parse_batch_name(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        batch_name = _parse_batch_name(d.pop("batch_name"))

        def _parse_bitrate(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        bitrate = _parse_bitrate(d.pop("bitrate"))

        def _parse_cover_url(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        cover_url = _parse_cover_url(d.pop("cover_url"))

        created_at = isoparse(d.pop("created_at"))

        def _parse_error_message(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        error_message = _parse_error_message(d.pop("error_message"))

        def _parse_error_step(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        error_step = _parse_error_step(d.pop("error_step"))

        def _parse_finished_at(data: object) -> Union[None, datetime.datetime]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                finished_at_type_0 = isoparse(data)

                return finished_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, datetime.datetime], data)

        finished_at = _parse_finished_at(d.pop("finished_at"))

        id = UUID(d.pop("id"))

        def _parse_list_position(data: object) -> Union[None, int]:
            if data is None:
                return data
            return cast(Union[None, int], data)

        list_position = _parse_list_position(d.pop("list_position"))

        def _parse_output_format(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        output_format = _parse_output_format(d.pop("output_format"))

        def _parse_output_path(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        output_path = _parse_output_path(d.pop("output_path"))

        def _parse_output_template(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        output_template = _parse_output_template(d.pop("output_template"))

        progress = d.pop("progress")

        def _parse_skip_reason(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        skip_reason = _parse_skip_reason(d.pop("skip_reason"))

        def _parse_started_at(data: object) -> Union[None, datetime.datetime]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                started_at_type_0 = isoparse(data)

                return started_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, datetime.datetime], data)

        started_at = _parse_started_at(d.pop("started_at"))

        status = DownloadStatus(d.pop("status"))

        def _parse_track_id(data: object) -> Union[None, UUID]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                track_id_type_0 = UUID(data)

                return track_id_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, UUID], data)

        track_id = _parse_track_id(d.pop("track_id"))

        def _parse_track_name(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        track_name = _parse_track_name(d.pop("track_name"))

        download_job_out = cls(
            artists=artists,
            batch_id=batch_id,
            batch_kind=batch_kind,
            batch_name=batch_name,
            bitrate=bitrate,
            cover_url=cover_url,
            created_at=created_at,
            error_message=error_message,
            error_step=error_step,
            finished_at=finished_at,
            id=id,
            list_position=list_position,
            output_format=output_format,
            output_path=output_path,
            output_template=output_template,
            progress=progress,
            skip_reason=skip_reason,
            started_at=started_at,
            status=status,
            track_id=track_id,
            track_name=track_name,
        )

        download_job_out.additional_properties = d
        return download_job_out

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
