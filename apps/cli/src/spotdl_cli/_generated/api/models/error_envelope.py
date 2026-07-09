from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.error_code import ErrorCode
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.error_envelope_detail_type_0 import ErrorEnvelopeDetailType0


T = TypeVar("T", bound="ErrorEnvelope")


@_attrs_define
class ErrorEnvelope:
    """The single wire shape for every error response body.

    ``code`` is typed as the closed :class:`ErrorCode` vocabulary (not a bare
    ``str``) so the exported OpenAPI documents the full enum and Plan 8's generated
    clients surface every code as a typed error (spec §10). It still serializes to
    its plain string value (``ErrorCode`` is a :class:`~enum.StrEnum`).

        Attributes:
            code (ErrorCode): The stable vocabulary of machine-readable error codes.
            message (str):
            detail (Union['ErrorEnvelopeDetailType0', None, Unset]):
    """

    code: ErrorCode
    message: str
    detail: Union["ErrorEnvelopeDetailType0", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.error_envelope_detail_type_0 import ErrorEnvelopeDetailType0

        code = self.code.value

        message = self.message

        detail: Union[None, Unset, dict[str, Any]]
        if isinstance(self.detail, Unset):
            detail = UNSET
        elif isinstance(self.detail, ErrorEnvelopeDetailType0):
            detail = self.detail.to_dict()
        else:
            detail = self.detail

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "code": code,
                "message": message,
            }
        )
        if detail is not UNSET:
            field_dict["detail"] = detail

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.error_envelope_detail_type_0 import ErrorEnvelopeDetailType0

        d = dict(src_dict)
        code = ErrorCode(d.pop("code"))

        message = d.pop("message")

        def _parse_detail(data: object) -> Union["ErrorEnvelopeDetailType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                detail_type_0 = ErrorEnvelopeDetailType0.from_dict(data)

                return detail_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ErrorEnvelopeDetailType0", None, Unset], data)

        detail = _parse_detail(d.pop("detail", UNSET))

        error_envelope = cls(
            code=code,
            message=message,
            detail=detail,
        )

        error_envelope.additional_properties = d
        return error_envelope

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
