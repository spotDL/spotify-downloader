from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.download_batch_out import DownloadBatchOut


T = TypeVar("T", bound="DownloadSubmitResponse")


@_attrs_define
class DownloadSubmitResponse:
    """``POST /downloads`` (201) body: the created batch + its jobs.

    Attributes:
        batch (DownloadBatchOut): A submission (batch) with its per-status tally and job listing.
    """

    batch: "DownloadBatchOut"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.download_batch_out import DownloadBatchOut

        batch = self.batch.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "batch": batch,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.download_batch_out import DownloadBatchOut

        d = dict(src_dict)
        batch = DownloadBatchOut.from_dict(d.pop("batch"))

        download_submit_response = cls(
            batch=batch,
        )

        download_submit_response.additional_properties = d
        return download_submit_response

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
