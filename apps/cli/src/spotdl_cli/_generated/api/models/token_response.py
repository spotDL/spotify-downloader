from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.user_response import UserResponse


T = TypeVar("T", bound="TokenResponse")


@_attrs_define
class TokenResponse:
    """A minted session: the access JWT, the rotating refresh token, and profile.

    ``token_type`` is always ``"bearer"`` and ``expires_in`` is the access
    token's remaining lifetime in seconds (``settings.access_token_ttl_seconds``),
    so a client knows when to refresh without decoding the JWT.

        Attributes:
            access_token (str):
            expires_in (int):
            refresh_token (str):
            user (UserResponse): The authenticated profile (``GET /auth/me`` body; nested in tokens).

                Built straight from the ``User`` ORM row via ``from_attributes`` — the router
                hands the service's ``User`` to :meth:`model_validate`; it never touches ORM
                types by name. The password hash is intentionally absent.
            token_type (Union[Unset, str]):  Default: 'bearer'.
    """

    access_token: str
    expires_in: int
    refresh_token: str
    user: "UserResponse"
    token_type: Union[Unset, str] = "bearer"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.user_response import UserResponse

        access_token = self.access_token

        expires_in = self.expires_in

        refresh_token = self.refresh_token

        user = self.user.to_dict()

        token_type = self.token_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "access_token": access_token,
                "expires_in": expires_in,
                "refresh_token": refresh_token,
                "user": user,
            }
        )
        if token_type is not UNSET:
            field_dict["token_type"] = token_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.user_response import UserResponse

        d = dict(src_dict)
        access_token = d.pop("access_token")

        expires_in = d.pop("expires_in")

        refresh_token = d.pop("refresh_token")

        user = UserResponse.from_dict(d.pop("user"))

        token_type = d.pop("token_type", UNSET)

        token_response = cls(
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=refresh_token,
            user=user,
            token_type=token_type,
        )

        token_response.additional_properties = d
        return token_response

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
