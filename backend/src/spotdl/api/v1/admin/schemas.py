"""Admin API request and response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ====== Response Models ======


class AdminUserResponse(BaseModel):
    """Admin view of a user."""

    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    reputation_score: int
    last_login: datetime | None
    created_at: datetime
    matches_submitted: int = 0
    votes_cast: int = 0
    reports_submitted: int = 0

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin."""

    users: list[AdminUserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class EntityCountsResponse(BaseModel):
    """Entity counts for dashboard."""

    songs: int
    artists: int
    albums: int
    playlists: int
    relations: int
    users: int


class GrowthStatsResponse(BaseModel):
    """Growth statistics."""

    entities_today: int
    entities_this_week: int
    relations_today: int
    relations_this_week: int
    new_users_today: int
    new_users_this_week: int


class SystemStatsResponse(BaseModel):
    """Complete system statistics."""

    entities: EntityCountsResponse
    growth: GrowthStatsResponse
    uptime_seconds: int


class AdminMatchResponse(BaseModel):
    """Admin view of a match (entity relation)."""

    id: str
    source_url: str
    source_platform: str
    target_url: str
    target_platform: str
    score: float | None
    confidence: float
    match_type: str
    status: str
    upvotes: int
    downvotes: int
    net_votes: int
    created_at: datetime
    discovered_by: str | None


class AdminMatchListResponse(BaseModel):
    """Paginated list of matches for admin."""

    matches: list[AdminMatchResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class MatchExportResponse(BaseModel):
    """Export response for matches."""

    exported_at: str
    count: int
    filter_status: str
    matches: list[AdminMatchResponse]


class UserExportItem(BaseModel):
    """Single user in export."""

    id: str
    username: str
    is_admin: bool
    is_active: bool
    reputation_score: int
    matches_submitted: int
    votes_cast: int
    reports_submitted: int
    created_at: str


class UserExportResponse(BaseModel):
    """Export response for users."""

    exported_at: str
    count: int
    users: list[UserExportItem]


class StatisticsExportResponse(BaseModel):
    """Export response for statistics."""

    exported_at: str
    entities: EntityCountsResponse
    growth: GrowthStatsResponse
    uptime_seconds: int
    matches_by_status: dict[str, int]
    users_by_reputation_tier: dict[str, int]


# ====== Request Models ======


class UpdateUserRequest(BaseModel):
    """Request to update a user's admin-editable fields."""

    is_active: bool | None = None
    is_admin: bool | None = None
    reputation_score: int | None = None


class UpdateMatchStatusRequest(BaseModel):
    """Request to update a match's status."""

    status: str


class ImportMatchItem(BaseModel):
    """Single match import item."""

    source_url: str
    source_platform: str | None = None
    target_url: str
    target_platform: str | None = None
    score: float | None = None
    match_type: str | None = None
    status: str | None = None


class ImportMatchesRequest(BaseModel):
    """Request to import matches."""

    matches: list[ImportMatchItem]


class BulkUrlImportRequest(BaseModel):
    """Request to import URLs."""

    urls: list[str]
