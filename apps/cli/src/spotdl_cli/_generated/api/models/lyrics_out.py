from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.lyrics_kind import LyricsKind
from ..models.provider_id import ProviderId
from ..types import UNSET, Unset

T = TypeVar("T", bound="LyricsOut")


@_attrs_define
class LyricsOut:
    """One lyrics variant for a track (``GET /tracks/{id}/lyrics`` element).

    Attributes:
        downvotes (int):
        id (str):
        kind (LyricsKind):
        net_score (int):
        source (ProviderId):
        text (str):
        upvotes (int):
    """

    downvotes: int
    id: str
    kind: LyricsKind
    net_score: int
    source: ProviderId
    text: str
    upvotes: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        downvotes = self.downvotes

        id = self.id

        kind = self.kind.value

        net_score = self.net_score

        source = self.source.value

        text = self.text

        upvotes = self.upvotes

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "downvotes": downvotes,
                "id": id,
                "kind": kind,
                "net_score": net_score,
                "source": source,
                "text": text,
                "upvotes": upvotes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        downvotes = d.pop("downvotes")

        id = d.pop("id")

        kind = LyricsKind(d.pop("kind"))

        net_score = d.pop("net_score")

        source = ProviderId(d.pop("source"))

        text = d.pop("text")

        upvotes = d.pop("upvotes")

        lyrics_out = cls(
            downvotes=downvotes,
            id=id,
            kind=kind,
            net_score=net_score,
            source=source,
            text=text,
            upvotes=upvotes,
        )

        lyrics_out.additional_properties = d
        return lyrics_out

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
