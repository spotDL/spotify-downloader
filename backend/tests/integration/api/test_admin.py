"""Tests for admin API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.db.models.album import Album
from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.models.match import Match, MatchType
from spotdl.db.models.metadata_report import MetadataReport, ReportStatus
from spotdl.db.models.playlist import Playlist
from spotdl.db.models.song import Song
from spotdl.db.models.user import User
from spotdl.db.models.vote import Vote, VoteType

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for testing."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        username="adminuser",
        email="admin@example.com",
        hashed_password="hashed_password_here",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_token(admin_user: User) -> str:
    """Create an auth token for the admin user."""
    from spotdl.core.security import create_access_token
    return create_access_token(str(admin_user.id))


@pytest.fixture
async def admin_client(
    db_session: AsyncSession, admin_token: str
) -> AsyncClient:
    """Create an authenticated admin client."""
    from spotdl.db.database import get_db_session
    from spotdl.main import app
    from httpx import ASGITransport

    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a regular non-admin user for testing."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        username="regularuser",
        email="regular@example.com",
        hashed_password="hashed_password_here",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ====== Authentication/Authorization Tests ======


class TestAdminAuthentication:
    """Tests for admin authentication and authorization."""

    async def test_admin_endpoint_requires_authentication(self, client: AsyncClient) -> None:
        """Test that admin endpoints require authentication."""
        response = await client.get("/api/v1/admin/users")
        assert response.status_code == 401

    async def test_admin_endpoint_requires_admin_role(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test that non-admin users get 403 on admin endpoints."""
        response = await authenticated_client.get("/api/v1/admin/users")
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    async def test_admin_can_access_admin_endpoints(
        self, admin_client: AsyncClient
    ) -> None:
        """Test that admin users can access admin endpoints."""
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code == 200


# ====== User Management Tests ======


class TestListUsers:
    """Tests for GET /api/v1/admin/users."""

    async def test_list_users_success(
        self, admin_client: AsyncClient, test_user: User, admin_user: User
    ) -> None:
        """Test listing users successfully."""
        response = await admin_client.get("/api/v1/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert data["total"] >= 2  # At least test_user and admin_user

    async def test_list_users_pagination(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test user list pagination."""
        # Create multiple users
        for i in range(5):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password="hashed",
            )
            db_session.add(user)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/admin/users", params={"page": 1, "per_page": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 3
        assert data["per_page"] == 3
        assert data["page"] == 1

    async def test_list_users_search(
        self, admin_client: AsyncClient, test_user: User
    ) -> None:
        """Test searching users by username."""
        response = await admin_client.get(
            "/api/v1/admin/users", params={"search": test_user.username}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(u["username"] == test_user.username for u in data["users"])

    async def test_list_users_filter_by_admin(
        self, admin_client: AsyncClient, test_user: User, admin_user: User
    ) -> None:
        """Test filtering users by admin status."""
        response = await admin_client.get(
            "/api/v1/admin/users", params={"is_admin": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(u["is_admin"] for u in data["users"])

    async def test_list_users_filter_by_active(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test filtering users by active status."""
        # Create inactive user
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            hashed_password="hashed",
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/admin/users", params={"is_active": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all(not u["is_active"] for u in data["users"])

    async def test_list_users_sorting(self, admin_client: AsyncClient) -> None:
        """Test sorting users."""
        response = await admin_client.get(
            "/api/v1/admin/users",
            params={"sort_by": "username", "sort_order": "asc"},
        )

        assert response.status_code == 200
        data = response.json()
        if len(data["users"]) > 1:
            usernames = [u["username"] for u in data["users"]]
            assert usernames == sorted(usernames)


class TestGetUser:
    """Tests for GET /api/v1/admin/users/{user_id}."""

    async def test_get_user_success(
        self, admin_client: AsyncClient, test_user: User
    ) -> None:
        """Test getting a user by ID."""
        response = await admin_client.get(f"/api/v1/admin/users/{test_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "matches_submitted" in data
        assert "votes_cast" in data
        assert "reports_submitted" in data

    async def test_get_user_not_found(self, admin_client: AsyncClient) -> None:
        """Test getting non-existent user returns 404."""
        fake_id = str(uuid.uuid4())
        response = await admin_client.get(f"/api/v1/admin/users/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_user_invalid_uuid(self, admin_client: AsyncClient) -> None:
        """Test getting user with invalid UUID returns 400."""
        response = await admin_client.get("/api/v1/admin/users/invalid-uuid")

        assert response.status_code == 400
        assert "Invalid user ID" in response.json()["detail"]


class TestUpdateUser:
    """Tests for PATCH /api/v1/admin/users/{user_id}."""

    async def test_update_user_is_active(
        self, admin_client: AsyncClient, test_user: User, db_session: AsyncSession
    ) -> None:
        """Test updating user's active status."""
        response = await admin_client.patch(
            f"/api/v1/admin/users/{test_user.id}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

        # Verify in database
        await db_session.refresh(test_user)
        assert test_user.is_active is False

    async def test_update_user_is_admin(
        self, admin_client: AsyncClient, test_user: User, db_session: AsyncSession
    ) -> None:
        """Test updating user's admin status."""
        response = await admin_client.patch(
            f"/api/v1/admin/users/{test_user.id}",
            json={"is_admin": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

        # Verify in database
        await db_session.refresh(test_user)
        assert test_user.is_admin is True

    async def test_update_user_reputation(
        self, admin_client: AsyncClient, test_user: User, db_session: AsyncSession
    ) -> None:
        """Test updating user's reputation score."""
        new_reputation = 500
        response = await admin_client.patch(
            f"/api/v1/admin/users/{test_user.id}",
            json={"reputation_score": new_reputation},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reputation_score"] == new_reputation

        # Verify in database
        await db_session.refresh(test_user)
        assert test_user.reputation_score == new_reputation

    async def test_update_user_cannot_self_demote(
        self, admin_client: AsyncClient, admin_user: User
    ) -> None:
        """Test that admin cannot remove their own admin status."""
        response = await admin_client.patch(
            f"/api/v1/admin/users/{admin_user.id}",
            json={"is_admin": False},
        )

        assert response.status_code == 400
        assert "Cannot remove your own admin status" in response.json()["detail"]

    async def test_update_user_not_found(self, admin_client: AsyncClient) -> None:
        """Test updating non-existent user returns 404."""
        fake_id = str(uuid.uuid4())
        response = await admin_client.patch(
            f"/api/v1/admin/users/{fake_id}",
            json={"is_active": False},
        )

        assert response.status_code == 404

    async def test_update_user_invalid_uuid(self, admin_client: AsyncClient) -> None:
        """Test updating user with invalid UUID returns 400."""
        response = await admin_client.patch(
            "/api/v1/admin/users/invalid-id",
            json={"is_active": False},
        )

        assert response.status_code == 400


# ====== Match Management Tests ======


class TestListMatches:
    """Tests for GET /api/v1/admin/matches."""

    async def test_list_matches_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test listing matches successfully."""
        # Create test match
        match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/test",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=test",
            match_type=MatchType.SYSTEM,
            match_score=85.0,
            status="pending",
        )
        db_session.add(match)
        await db_session.commit()

        response = await admin_client.get("/api/v1/admin/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 1

    async def test_list_matches_pagination(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test match list pagination."""
        # Create multiple matches
        for i in range(5):
            match = Match(
                source_platform="spotify",
                source_url=f"https://open.spotify.com/track/test{i}",
                target_platform="youtube",
                target_url=f"https://youtube.com/watch?v=test{i}",
                match_type=MatchType.SYSTEM,
                match_score=80.0,
            )
            db_session.add(match)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/admin/matches", params={"page": 1, "per_page": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) <= 3
        assert data["per_page"] == 3

    async def test_list_matches_filter_by_status(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test filtering matches by status."""
        # Create verified match
        verified_match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/verified",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=verified",
            match_type=MatchType.SYSTEM,
            status="verified",
        )
        db_session.add(verified_match)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/admin/matches", params={"status": "verified"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(m["status"] == "verified" for m in data["matches"])

    async def test_list_matches_filter_by_type(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test filtering matches by type."""
        # Create user-submitted match
        user_match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/user",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=user",
            match_type=MatchType.USER_SUBMITTED,
        )
        db_session.add(user_match)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/admin/matches", params={"match_type": "user_submitted"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should filter correctly
        assert response.status_code == 200


class TestUpdateMatchStatus:
    """Tests for PATCH /api/v1/admin/matches/{match_id}."""

    async def test_verify_match(
        self, admin_client: AsyncClient, db_session: AsyncSession, admin_user: User
    ) -> None:
        """Test verifying a match."""
        match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/test",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=test",
            match_type=MatchType.SYSTEM,
            status="pending",
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)

        response = await admin_client.patch(
            f"/api/v1/admin/matches/{match.id}",
            json={"status": "verified"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["verified_by"] == str(admin_user.id)

    async def test_reject_match(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test rejecting a match."""
        match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/reject",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=reject",
            match_type=MatchType.SYSTEM,
            status="pending",
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)

        response = await admin_client.patch(
            f"/api/v1/admin/matches/{match.id}",
            json={"status": "rejected"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    async def test_verify_match_awards_reputation(
        self, admin_client: AsyncClient, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that verifying a match awards reputation to submitter."""
        initial_reputation = test_user.reputation_score

        match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/rep",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=rep",
            match_type=MatchType.USER_SUBMITTED,
            status="pending",
            submitted_by=test_user.id,
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)

        response = await admin_client.patch(
            f"/api/v1/admin/matches/{match.id}",
            json={"status": "verified"},
        )

        assert response.status_code == 200

        # Check reputation increased
        await db_session.refresh(test_user)
        assert test_user.reputation_score > initial_reputation

    async def test_reject_match_deducts_reputation(
        self, admin_client: AsyncClient, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that rejecting a match deducts reputation from submitter."""
        # Set initial reputation
        test_user.reputation_score = 100
        await db_session.commit()

        match = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/rep2",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=rep2",
            match_type=MatchType.USER_SUBMITTED,
            status="pending",
            submitted_by=test_user.id,
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)
        initial_reputation = test_user.reputation_score

        response = await admin_client.patch(
            f"/api/v1/admin/matches/{match.id}",
            json={"status": "rejected"},
        )

        assert response.status_code == 200

        # Check reputation decreased
        await db_session.refresh(test_user)
        assert test_user.reputation_score < initial_reputation

    async def test_update_match_not_found(self, admin_client: AsyncClient) -> None:
        """Test updating non-existent match returns 404."""
        fake_id = str(uuid.uuid4())
        response = await admin_client.patch(
            f"/api/v1/admin/matches/{fake_id}",
            json={"status": "verified"},
        )

        assert response.status_code == 404

    async def test_update_match_invalid_uuid(self, admin_client: AsyncClient) -> None:
        """Test updating match with invalid UUID returns 400."""
        response = await admin_client.patch(
            "/api/v1/admin/matches/invalid-id",
            json={"status": "verified"},
        )

        assert response.status_code == 400


# ====== Statistics Tests ======


class TestGetSystemStats:
    """Tests for GET /api/v1/admin/stats."""

    async def test_get_stats_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test getting system statistics."""
        # Create some test data
        artist = Artist(name="Test Artist", platform="spotify", platform_id="artist1")
        db_session.add(artist)
        await db_session.commit()

        response = await admin_client.get("/api/v1/admin/stats")

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "growth" in data
        assert "uptime_seconds" in data

        # Check entities structure
        entities = data["entities"]
        assert "songs" in entities
        assert "artists" in entities
        assert "albums" in entities
        assert "playlists" in entities
        assert "matches" in entities
        assert "users" in entities
        assert entities["artists"] >= 1

        # Check growth structure
        growth = data["growth"]
        assert "songs_today" in growth
        assert "songs_this_week" in growth
        assert "matches_today" in growth
        assert "matches_this_week" in growth
        assert "new_users_today" in growth
        assert "new_users_this_week" in growth

    async def test_stats_counts_entities_correctly(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that stats correctly count entities."""
        # Create test entities
        artist = Artist(name="Artist", platform="spotify", platform_id="a1")
        album = Album(
            title="Album",
            artist_name="Artist",
            platform="spotify",
            platform_id="album1",
        )
        db_session.add_all([artist, album])
        await db_session.commit()

        response = await admin_client.get("/api/v1/admin/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["entities"]["artists"] >= 1
        assert data["entities"]["albums"] >= 1


# ====== Import Tests ======


class TestImportMatches:
    """Tests for POST /api/v1/admin/import/matches."""

    async def test_import_matches_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test importing matches from JSON."""
        matches_data = [
            {
                "source_url": "https://open.spotify.com/track/import1",
                "source_platform": "spotify",
                "target_url": "https://youtube.com/watch?v=import1",
                "target_platform": "youtube",
                "score": 90.0,
                "match_type": "imported",
                "status": "verified",
            },
            {
                "source_url": "https://open.spotify.com/track/import2",
                "source_platform": "spotify",
                "target_url": "https://youtube.com/watch?v=import2",
                "target_platform": "youtube",
            },
        ]

        response = await admin_client.post(
            "/api/v1/admin/import/matches",
            json={"matches": matches_data},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 2
        assert data["skipped"] == 0

    async def test_import_matches_skips_duplicates(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that duplicate matches are skipped."""
        # Create existing match
        existing = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/exists",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=exists",
            match_type=MatchType.SYSTEM,
        )
        db_session.add(existing)
        await db_session.commit()

        # Try to import the same match
        matches_data = [
            {
                "source_url": "https://open.spotify.com/track/exists",
                "target_url": "https://youtube.com/watch?v=exists",
            }
        ]

        response = await admin_client.post(
            "/api/v1/admin/import/matches",
            json={"matches": matches_data},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skipped"] == 1
        assert data["imported"] == 0

    async def test_import_matches_handles_errors(
        self, admin_client: AsyncClient
    ) -> None:
        """Test that import handles missing required fields."""
        matches_data = [
            {
                # Missing required source_url
                "target_url": "https://youtube.com/watch?v=error",
            }
        ]

        response = await admin_client.post(
            "/api/v1/admin/import/matches",
            json={"matches": matches_data},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["errors"]) > 0


class TestImportUrls:
    """Tests for POST /api/v1/admin/import/urls."""

    async def test_import_urls_success(
        self, admin_client: AsyncClient
    ) -> None:
        """Test importing songs from URLs."""
        with patch("spotdl.api.v1.admin.get_song_service") as mock_service:
            from spotdl.core.types.song import Song, Platform

            mock_song = Song(
                name="Test Song",
                artists=("Artist",),
                artist="Artist",
                duration=180,
                platform=Platform.SPOTIFY,
                platform_id="test123",
                url="https://open.spotify.com/track/test123",
                genres=(),
            )

            mock_svc = MagicMock()
            mock_svc.resolve_url = AsyncMock(return_value=[mock_song])
            mock_service.return_value = mock_svc

            response = await admin_client.post(
                "/api/v1/admin/import/urls",
                json={"urls": ["https://open.spotify.com/track/test123"]},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["resolved"] >= 1

    async def test_import_urls_handles_unsupported(
        self, admin_client: AsyncClient
    ) -> None:
        """Test importing unsupported URLs."""
        with patch("spotdl.api.v1.admin.get_song_service") as mock_service:
            from spotdl.core.services.song import UnsupportedURLError

            mock_svc = MagicMock()
            mock_svc.resolve_url = AsyncMock(side_effect=UnsupportedURLError("Unsupported"))
            mock_service.return_value = mock_svc

            response = await admin_client.post(
                "/api/v1/admin/import/urls",
                json={"urls": ["https://unsupported.com/track/123"]},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["skipped"] >= 1
            assert len(data["errors"]) > 0


# ====== Danger Zone Tests ======


class TestPurgeUnverifiedMatches:
    """Tests for DELETE /api/v1/admin/matches/unverified."""

    async def test_purge_dry_run(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test purge dry run without confirm parameter."""
        # Create pending and rejected matches
        pending = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/pend",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=pend",
            match_type=MatchType.SYSTEM,
            status="pending",
        )
        rejected = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/rej",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=rej",
            match_type=MatchType.SYSTEM,
            status="rejected",
        )
        db_session.add_all([pending, rejected])
        await db_session.commit()

        response = await admin_client.delete("/api/v1/admin/matches/unverified")

        assert response.status_code == 200
        data = response.json()
        assert "Dry run" in data["message"]
        assert data["total_to_delete"] >= 2

    async def test_purge_with_confirm(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test purge with confirm parameter actually deletes."""
        # Create matches
        pending = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/purge",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=purge",
            match_type=MatchType.SYSTEM,
            status="pending",
        )
        db_session.add(pending)
        await db_session.commit()

        response = await admin_client.delete(
            "/api/v1/admin/matches/unverified", params={"confirm": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] >= 1

        # Verify deletion
        result = await db_session.execute(
            select(Match).where(Match.status == "pending")
        )
        assert len(result.scalars().all()) == 0


class TestResetDatabase:
    """Tests for DELETE /api/v1/admin/reset-database."""

    async def test_reset_dry_run(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test reset dry run without confirm parameter."""
        # Create test data
        artist = Artist(name="Artist", platform="spotify", platform_id="a1")
        db_session.add(artist)
        await db_session.commit()

        response = await admin_client.delete("/api/v1/admin/reset-database")

        assert response.status_code == 200
        data = response.json()
        assert "Dry run" in data["message"]
        assert "RESET" in data["message"]
        assert data["users_preserved"] is True

    async def test_reset_with_wrong_confirm(
        self, admin_client: AsyncClient
    ) -> None:
        """Test reset with wrong confirm value."""
        response = await admin_client.delete(
            "/api/v1/admin/reset-database", params={"confirm": "wrong"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "Dry run" in data["message"]

    async def test_reset_with_correct_confirm(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test reset with correct confirm parameter."""
        # Create test data
        artist = Artist(name="Artist", platform="spotify", platform_id="a1")
        db_session.add(artist)
        await db_session.commit()

        response = await admin_client.delete(
            "/api/v1/admin/reset-database", params={"confirm": "RESET"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset complete" in data["message"].lower()
        assert data["users_preserved"] is True

        # Verify data is deleted
        result = await db_session.execute(select(Artist))
        assert len(result.scalars().all()) == 0


# ====== Export Tests ======


class TestExportMatches:
    """Tests for GET /api/v1/admin/export/matches."""

    async def test_export_matches_default_verified(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test exporting matches defaults to verified only."""
        # Create verified and pending matches
        verified = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/ver",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=ver",
            match_type=MatchType.SYSTEM,
            status="verified",
        )
        pending = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/pend",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=pend",
            match_type=MatchType.SYSTEM,
            status="pending",
        )
        db_session.add_all([verified, pending])
        await db_session.commit()

        response = await admin_client.get("/api/v1/admin/export/matches")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "count" in data
        assert data["filter_status"] == "verified"
        assert all(m["status"] == "verified" for m in data["matches"])

    async def test_export_matches_with_status_filter(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test exporting matches with status filter."""
        pending = Match(
            source_platform="spotify",
            source_url="https://open.spotify.com/track/p1",
            target_platform="youtube",
            target_url="https://youtube.com/watch?v=p1",
            match_type=MatchType.SYSTEM,
            status="pending",
        )
        db_session.add(pending)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/admin/export/matches", params={"status": "pending"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filter_status"] == "pending"


class TestExportUsers:
    """Tests for GET /api/v1/admin/export/users."""

    async def test_export_users_success(
        self, admin_client: AsyncClient, test_user: User
    ) -> None:
        """Test exporting user data."""
        response = await admin_client.get("/api/v1/admin/export/users")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "count" in data
        assert data["count"] >= 1

        # Verify user data structure (sensitive data excluded)
        if data["users"]:
            user = data["users"][0]
            assert "id" in user
            assert "username" in user
            assert "email" not in user  # Email should not be in export
            assert "is_admin" in user
            assert "reputation_score" in user


class TestExportStatistics:
    """Tests for GET /api/v1/admin/export/statistics."""

    async def test_export_statistics_success(
        self, admin_client: AsyncClient
    ) -> None:
        """Test exporting complete statistics."""
        response = await admin_client.get("/api/v1/admin/export/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "exported_at" in data
        assert "entities" in data
        assert "growth" in data
        assert "uptime_seconds" in data
        assert "matches_by_status" in data
        assert "users_by_reputation_tier" in data

        # Verify matches by status
        matches_by_status = data["matches_by_status"]
        assert "pending" in matches_by_status
        assert "verified" in matches_by_status
        assert "rejected" in matches_by_status

        # Verify reputation tiers
        rep_tiers = data["users_by_reputation_tier"]
        assert "novice (0-99)" in rep_tiers
        assert "contributor (100-499)" in rep_tiers
        assert "trusted (500-999)" in rep_tiers
        assert "elite (1000+)" in rep_tiers
