from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.download_job_out import DownloadJobOut


T = TypeVar("T", bound="DownloadListResponse")


@_attrs_define
class DownloadListResponse:
    """``GET /downloads`` body: a page of jobs + pagination metadata.

    Attributes:
        jobs (list['DownloadJobOut']):
        limit (int):
        offset (int):
        total (int):
    """

    jobs: list["DownloadJobOut"]
    limit: int
    offset: int
    total: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.download_job_out import DownloadJobOut

        jobs = []
        for jobs_item_data in self.jobs:
            jobs_item = jobs_item_data.to_dict()
            jobs.append(jobs_item)

        limit = self.limit

        offset = self.offset

        total = self.total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "jobs": jobs,
                "limit": limit,
                "offset": offset,
                "total": total,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.download_job_out import DownloadJobOut

        d = dict(src_dict)
        jobs = []
        _jobs = d.pop("jobs")
        for jobs_item_data in _jobs:
            jobs_item = DownloadJobOut.from_dict(jobs_item_data)

            jobs.append(jobs_item)

        limit = d.pop("limit")

        offset = d.pop("offset")

        total = d.pop("total")

        download_list_response = cls(
            jobs=jobs,
            limit=limit,
            offset=offset,
            total=total,
        )

        download_list_response.additional_properties = d
        return download_list_response

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
