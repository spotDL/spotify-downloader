from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.match_status import MatchStatus
from ..models.provider_id import ProviderId
from ..types import UNSET, Unset

T = TypeVar("T", bound="MatchOut")


@_attrs_define
class MatchOut:
    """One ranked audio target for a track (``GET /tracks/{id}/matches`` element).

    Attributes:
        downvotes (int):
        id (str):
        matcher_version (str):
        net_score (int):
        score (float):
        status (MatchStatus):
        target_id (str):
        target_provider (ProviderId):
        target_url (str):
        upvotes (int):
        candidate_artists (Union[Unset, list[str]]):
        candidate_duration_ms (Union[None, Unset, int]):
        candidate_name (Union[None, Unset, str]):
    """

    downvotes: int
    id: str
    matcher_version: str
    net_score: int
    score: float
    status: MatchStatus
    target_id: str
    target_provider: ProviderId
    target_url: str
    upvotes: int
    candidate_artists: Union[Unset, list[str]] = UNSET
    candidate_duration_ms: Union[None, Unset, int] = UNSET
    candidate_name: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        downvotes = self.downvotes

        id = self.id

        matcher_version = self.matcher_version

        net_score = self.net_score

        score = self.score

        status = self.status.value

        target_id = self.target_id

        target_provider = self.target_provider.value

        target_url = self.target_url

        upvotes = self.upvotes

        candidate_artists: Union[Unset, list[str]] = UNSET
        if not isinstance(self.candidate_artists, Unset):
            candidate_artists = self.candidate_artists

        candidate_duration_ms: Union[None, Unset, int]
        if isinstance(self.candidate_duration_ms, Unset):
            candidate_duration_ms = UNSET
        else:
            candidate_duration_ms = self.candidate_duration_ms

        candidate_name: Union[None, Unset, str]
        if isinstance(self.candidate_name, Unset):
            candidate_name = UNSET
        else:
            candidate_name = self.candidate_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "downvotes": downvotes,
                "id": id,
                "matcher_version": matcher_version,
                "net_score": net_score,
                "score": score,
                "status": status,
                "target_id": target_id,
                "target_provider": target_provider,
                "target_url": target_url,
                "upvotes": upvotes,
            }
        )
        if candidate_artists is not UNSET:
            field_dict["candidate_artists"] = candidate_artists
        if candidate_duration_ms is not UNSET:
            field_dict["candidate_duration_ms"] = candidate_duration_ms
        if candidate_name is not UNSET:
            field_dict["candidate_name"] = candidate_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        downvotes = d.pop("downvotes")

        id = d.pop("id")

        matcher_version = d.pop("matcher_version")

        net_score = d.pop("net_score")

        score = d.pop("score")

        status = MatchStatus(d.pop("status"))

        target_id = d.pop("target_id")

        target_provider = ProviderId(d.pop("target_provider"))

        target_url = d.pop("target_url")

        upvotes = d.pop("upvotes")

        candidate_artists = cast(list[str], d.pop("candidate_artists", UNSET))

        def _parse_candidate_duration_ms(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        candidate_duration_ms = _parse_candidate_duration_ms(d.pop("candidate_duration_ms", UNSET))

        def _parse_candidate_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        candidate_name = _parse_candidate_name(d.pop("candidate_name", UNSET))

        match_out = cls(
            downvotes=downvotes,
            id=id,
            matcher_version=matcher_version,
            net_score=net_score,
            score=score,
            status=status,
            target_id=target_id,
            target_provider=target_provider,
            target_url=target_url,
            upvotes=upvotes,
            candidate_artists=candidate_artists,
            candidate_duration_ms=candidate_duration_ms,
            candidate_name=candidate_name,
        )

        match_out.additional_properties = d
        return match_out

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
