from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.votable_type import VotableType
from ..types import UNSET, Unset

T = TypeVar("T", bound="VoteResponse")


@_attrs_define
class VoteResponse:
    """The vote outcome: the votable's fresh tallies, derived status, and the
    caller's own vote (``+1`` / ``-1`` / ``null`` after a retract).

    Mirrors the service's :class:`~spotdl_server.services.voting.VoteOutcome`;
    ``status`` is ``null`` for lyrics (which have no status column).

        Attributes:
            downvotes (int):
            net_score (int):
            upvotes (int):
            votable_id (UUID):
            votable_type (VotableType): Polymorphic discriminator for ``votes.votable_type``.

                Values are the string form of the target table: ``votable_id`` points into
                ``matches.id`` / ``lyrics.id`` / ``entity_links.id`` respectively (no
                cross-table FK).
            status (Union[None, Unset, str]):
            your_vote (Union[None, Unset, int]):
    """

    downvotes: int
    net_score: int
    upvotes: int
    votable_id: UUID
    votable_type: VotableType
    status: Union[None, Unset, str] = UNSET
    your_vote: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        downvotes = self.downvotes

        net_score = self.net_score

        upvotes = self.upvotes

        votable_id = str(self.votable_id)

        votable_type = self.votable_type.value

        status: Union[None, Unset, str]
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        your_vote: Union[None, Unset, int]
        if isinstance(self.your_vote, Unset):
            your_vote = UNSET
        else:
            your_vote = self.your_vote

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "downvotes": downvotes,
                "net_score": net_score,
                "upvotes": upvotes,
                "votable_id": votable_id,
                "votable_type": votable_type,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if your_vote is not UNSET:
            field_dict["your_vote"] = your_vote

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        downvotes = d.pop("downvotes")

        net_score = d.pop("net_score")

        upvotes = d.pop("upvotes")

        votable_id = UUID(d.pop("votable_id"))

        votable_type = VotableType(d.pop("votable_type"))

        def _parse_status(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_your_vote(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        your_vote = _parse_your_vote(d.pop("your_vote", UNSET))

        vote_response = cls(
            downvotes=downvotes,
            net_score=net_score,
            upvotes=upvotes,
            votable_id=votable_id,
            votable_type=votable_type,
            status=status,
            your_vote=your_vote,
        )

        vote_response.additional_properties = d
        return vote_response

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
