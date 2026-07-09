import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.entity_type import EntityType
from ..models.report_status import ReportStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="ReportResponse")


@_attrs_define
class ReportResponse:
    """A metadata-correction report as returned by ``POST /reports`` / ``GET /reports/me``.

    Built straight from the ``Report`` ORM row via ``from_attributes`` — the router
    hands the service's ``Report`` to :meth:`model_validate`; it never names the
    ORM type. The admin-only review fields (``reviewed_by`` / ``reviewed_at`` /
    ``review_note``) are intentionally absent from the reporter-facing shape.

        Attributes:
            created_at (datetime.datetime):
            id (UUID):
            status (ReportStatus): Minimal review state of a metadata-correction ``reports`` row.
            subject_id (UUID):
            subject_type (EntityType):
            field (Union[None, Unset, str]):
            proposed_value (Union[None, Unset, str]):
            reason (Union[None, Unset, str]):
    """

    created_at: datetime.datetime
    id: UUID
    status: ReportStatus
    subject_id: UUID
    subject_type: EntityType
    field: Union[None, Unset, str] = UNSET
    proposed_value: Union[None, Unset, str] = UNSET
    reason: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        created_at = self.created_at.isoformat()

        id = str(self.id)

        status = self.status.value

        subject_id = str(self.subject_id)

        subject_type = self.subject_type.value

        field: Union[None, Unset, str]
        if isinstance(self.field, Unset):
            field = UNSET
        else:
            field = self.field

        proposed_value: Union[None, Unset, str]
        if isinstance(self.proposed_value, Unset):
            proposed_value = UNSET
        else:
            proposed_value = self.proposed_value

        reason: Union[None, Unset, str]
        if isinstance(self.reason, Unset):
            reason = UNSET
        else:
            reason = self.reason

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "created_at": created_at,
                "id": id,
                "status": status,
                "subject_id": subject_id,
                "subject_type": subject_type,
            }
        )
        if field is not UNSET:
            field_dict["field"] = field
        if proposed_value is not UNSET:
            field_dict["proposed_value"] = proposed_value
        if reason is not UNSET:
            field_dict["reason"] = reason

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        created_at = isoparse(d.pop("created_at"))

        id = UUID(d.pop("id"))

        status = ReportStatus(d.pop("status"))

        subject_id = UUID(d.pop("subject_id"))

        subject_type = EntityType(d.pop("subject_type"))

        def _parse_field(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        field = _parse_field(d.pop("field", UNSET))

        def _parse_proposed_value(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        proposed_value = _parse_proposed_value(d.pop("proposed_value", UNSET))

        def _parse_reason(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        reason = _parse_reason(d.pop("reason", UNSET))

        report_response = cls(
            created_at=created_at,
            id=id,
            status=status,
            subject_id=subject_id,
            subject_type=subject_type,
            field=field,
            proposed_value=proposed_value,
            reason=reason,
        )

        report_response.additional_properties = d
        return report_response

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
