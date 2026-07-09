from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.context import Context


T = TypeVar("T", bound="ValidationError")


@_attrs_define
class ValidationError:
    """
    Attributes:
        loc (list[Union[int, str]]):
        msg (str):
        type_ (str):
        ctx (Union[Unset, Context]):
        input_ (Union[Unset, Any]):
    """

    loc: list[Union[int, str]]
    msg: str
    type_: str
    ctx: Union[Unset, "Context"] = UNSET
    input_: Union[Unset, Any] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.context import Context

        loc = []
        for loc_item_data in self.loc:
            loc_item: Union[int, str]
            loc_item = loc_item_data
            loc.append(loc_item)

        msg = self.msg

        type_ = self.type_

        ctx: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.ctx, Unset):
            ctx = self.ctx.to_dict()

        input_ = self.input_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "loc": loc,
                "msg": msg,
                "type": type_,
            }
        )
        if ctx is not UNSET:
            field_dict["ctx"] = ctx
        if input_ is not UNSET:
            field_dict["input"] = input_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.context import Context

        d = dict(src_dict)
        loc = []
        _loc = d.pop("loc")
        for loc_item_data in _loc:

            def _parse_loc_item(data: object) -> Union[int, str]:
                return cast(Union[int, str], data)

            loc_item = _parse_loc_item(loc_item_data)

            loc.append(loc_item)

        msg = d.pop("msg")

        type_ = d.pop("type")

        _ctx = d.pop("ctx", UNSET)
        ctx: Union[Unset, Context]
        if isinstance(_ctx, Unset):
            ctx = UNSET
        else:
            ctx = Context.from_dict(_ctx)

        input_ = d.pop("input", UNSET)

        validation_error = cls(
            loc=loc,
            msg=msg,
            type_=type_,
            ctx=ctx,
            input_=input_,
        )

        validation_error.additional_properties = d
        return validation_error

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
