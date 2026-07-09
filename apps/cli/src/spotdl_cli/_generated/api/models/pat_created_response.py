import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="PatCreatedResponse")


@_attrs_define
class PatCreatedResponse:
    """``POST /auth/tokens`` body: the newly minted PAT, **including the secret**.

    This is the only response that carries ``token`` (the full ``spdl_pat_``
    secret); it is shown exactly once and never returned again — thereafter a
    client sees only :class:`PatResponse` (prefix + metadata). The client must
    store ``token`` now (e.g. the CLI writes it to its config).

        Attributes:
            created_at (datetime.datetime):
            id (UUID):
            name (str):
            token (str):
            token_prefix (str):
            expires_at (Union[None, Unset, datetime.datetime]):
    """

    created_at: datetime.datetime
    id: UUID
    name: str
    token: str
    token_prefix: str
    expires_at: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        created_at = self.created_at.isoformat()

        id = str(self.id)

        name = self.name

        token = self.token

        token_prefix = self.token_prefix

        expires_at: Union[None, Unset, str]
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        elif isinstance(self.expires_at, datetime.datetime):
            expires_at = self.expires_at.isoformat()
        else:
            expires_at = self.expires_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "created_at": created_at,
                "id": id,
                "name": name,
                "token": token,
                "token_prefix": token_prefix,
            }
        )
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        created_at = isoparse(d.pop("created_at"))

        id = UUID(d.pop("id"))

        name = d.pop("name")

        token = d.pop("token")

        token_prefix = d.pop("token_prefix")

        def _parse_expires_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                expires_at_type_0 = isoparse(data)

                return expires_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        pat_created_response = cls(
            created_at=created_at,
            id=id,
            name=name,
            token=token,
            token_prefix=token_prefix,
            expires_at=expires_at,
        )

        pat_created_response.additional_properties = d
        return pat_created_response

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
