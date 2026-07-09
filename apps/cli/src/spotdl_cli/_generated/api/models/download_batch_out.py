from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.batch_kind import BatchKind
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.counts import Counts
    from ..models.download_job_out import DownloadJobOut


T = TypeVar("T", bound="DownloadBatchOut")


@_attrs_define
class DownloadBatchOut:
    """A submission (batch) with its per-status tally and job listing.

    Attributes:
        batch_id (UUID):
        counts (Counts):
        finalized (bool):
        jobs (list['DownloadJobOut']):
        kind (BatchKind): Shape of a ``download_batches`` submission (Plan 7).
        name (Union[None, str]):
        total_jobs (int):
    """

    batch_id: UUID
    counts: "Counts"
    finalized: bool
    jobs: list["DownloadJobOut"]
    kind: BatchKind
    name: Union[None, str]
    total_jobs: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.counts import Counts
        from ..models.download_job_out import DownloadJobOut

        batch_id = str(self.batch_id)

        counts = self.counts.to_dict()

        finalized = self.finalized

        jobs = []
        for jobs_item_data in self.jobs:
            jobs_item = jobs_item_data.to_dict()
            jobs.append(jobs_item)

        kind = self.kind.value

        name: Union[None, str]
        name = self.name

        total_jobs = self.total_jobs

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "batch_id": batch_id,
                "counts": counts,
                "finalized": finalized,
                "jobs": jobs,
                "kind": kind,
                "name": name,
                "total_jobs": total_jobs,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.counts import Counts
        from ..models.download_job_out import DownloadJobOut

        d = dict(src_dict)
        batch_id = UUID(d.pop("batch_id"))

        counts = Counts.from_dict(d.pop("counts"))

        finalized = d.pop("finalized")

        jobs = []
        _jobs = d.pop("jobs")
        for jobs_item_data in _jobs:
            jobs_item = DownloadJobOut.from_dict(jobs_item_data)

            jobs.append(jobs_item)

        kind = BatchKind(d.pop("kind"))

        def _parse_name(data: object) -> Union[None, str]:
            if data is None:
                return data
            return cast(Union[None, str], data)

        name = _parse_name(d.pop("name"))

        total_jobs = d.pop("total_jobs")

        download_batch_out = cls(
            batch_id=batch_id,
            counts=counts,
            finalized=finalized,
            jobs=jobs,
            kind=kind,
            name=name,
            total_jobs=total_jobs,
        )

        download_batch_out.additional_properties = d
        return download_batch_out

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
