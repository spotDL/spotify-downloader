import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="AdminUserResponse")


@_attrs_define
class AdminUserResponse:
    """A user as it appears in the admin user list (``GET /admin/users`` element).

    Built straight from the ``User`` ORM row via ``from_attributes``; the router
    never names the ORM type. Unlike the auth-facing :class:`UserResponse` this
    exposes the moderation-relevant ``is_active`` flag. The password hash is
    intentionally absent.

        Attributes:
            created_at (datetime.datetime):
            email (str):
            id (UUID):
            is_active (bool):
            is_admin (bool):
            display_name (Union[None, Unset, str]):
    """

    created_at: datetime.datetime
    email: str
    id: UUID
    is_active: bool
    is_admin: bool
    display_name: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        created_at = self.created_at.isoformat()

        email = self.email

        id = str(self.id)

        is_active = self.is_active

        is_admin = self.is_admin

        display_name: Union[None, Unset, str]
        if isinstance(self.display_name, Unset):
            display_name = UNSET
        else:
            display_name = self.display_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "created_at": created_at,
                "email": email,
                "id": id,
                "is_active": is_active,
                "is_admin": is_admin,
            }
        )
        if display_name is not UNSET:
            field_dict["display_name"] = display_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        created_at = isoparse(d.pop("created_at"))

        email = d.pop("email")

        id = UUID(d.pop("id"))

        is_active = d.pop("is_active")

        is_admin = d.pop("is_admin")

        def _parse_display_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        display_name = _parse_display_name(d.pop("display_name", UNSET))

        admin_user_response = cls(
            created_at=created_at,
            email=email,
            id=id,
            is_active=is_active,
            is_admin=is_admin,
            display_name=display_name,
        )

        admin_user_response.additional_properties = d
        return admin_user_response

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
