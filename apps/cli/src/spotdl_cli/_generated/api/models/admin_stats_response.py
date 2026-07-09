from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AdminStatsResponse")


@_attrs_define
class AdminStatsResponse:
    """``GET /admin/stats`` body: aggregate community-health counts.

    Mirrors the service's :class:`~spotdl_server.services.admin.AdminStats`
    dataclass field-for-field (built via ``from_attributes``).

        Attributes:
            community_verified_matches (int):
            matches_total (int):
            rejected_matches (int):
            reports_pending (int):
            reports_total (int):
            users_total (int):
            votes_total (int):
    """

    community_verified_matches: int
    matches_total: int
    rejected_matches: int
    reports_pending: int
    reports_total: int
    users_total: int
    votes_total: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        community_verified_matches = self.community_verified_matches

        matches_total = self.matches_total

        rejected_matches = self.rejected_matches

        reports_pending = self.reports_pending

        reports_total = self.reports_total

        users_total = self.users_total

        votes_total = self.votes_total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "community_verified_matches": community_verified_matches,
                "matches_total": matches_total,
                "rejected_matches": rejected_matches,
                "reports_pending": reports_pending,
                "reports_total": reports_total,
                "users_total": users_total,
                "votes_total": votes_total,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        community_verified_matches = d.pop("community_verified_matches")

        matches_total = d.pop("matches_total")

        rejected_matches = d.pop("rejected_matches")

        reports_pending = d.pop("reports_pending")

        reports_total = d.pop("reports_total")

        users_total = d.pop("users_total")

        votes_total = d.pop("votes_total")

        admin_stats_response = cls(
            community_verified_matches=community_verified_matches,
            matches_total=matches_total,
            rejected_matches=rejected_matches,
            reports_pending=reports_pending,
            reports_total=reports_total,
            users_total=users_total,
            votes_total=votes_total,
        )

        admin_stats_response.additional_properties = d
        return admin_stats_response

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
