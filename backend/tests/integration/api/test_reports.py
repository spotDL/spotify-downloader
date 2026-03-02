"""Tests for metadata reports API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.reputation import ReputationReward
from spotdl.db.models.metadata_report import (
    MetadataReport,
    MetadataReportEntityType,
    ReportStatus,
)
from spotdl.db.models.user import User

pytestmark = pytest.mark.asyncio


# ====== Fixtures ======


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
async def admin_client(db_session: AsyncSession, admin_token: str) -> AsyncClient:
    """Create an authenticated admin client."""
    from httpx import ASGITransport

    from spotdl.db.database import get_db_session
    from spotdl.main import app

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
async def test_report(db_session: AsyncSession, test_user: User) -> MetadataReport:
    """Create a test report."""
    report = MetadataReport(
        entity_type=MetadataReportEntityType.SONG.value,
        entity_id=uuid.UUID("00000000-0000-0000-0000-000000000100"),
        reporter_id=test_user.id,
        field_name="title",
        current_value="Wrong Title",
        suggested_value="Correct Title",
        description="The title is incorrect",
        status=ReportStatus.PENDING.value,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


# ====== Report Creation Tests ======


class TestCreateReport:
    """Tests for POST /api/v1/reports."""

    async def test_create_report_success(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test creating a metadata report successfully."""
        initial_reputation = test_user.reputation_score
        entity_id = str(uuid.uuid4())

        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": entity_id,
                "field_name": "artist",
                "current_value": "Wrong Artist",
                "suggested_value": "Correct Artist",
                "description": "Artist name is incorrect",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "song"
        assert data["entity_id"] == entity_id
        assert data["field_name"] == "artist"
        assert data["current_value"] == "Wrong Artist"
        assert data["suggested_value"] == "Correct Artist"
        assert data["description"] == "Artist name is incorrect"
        assert data["status"] == "pending"
        assert data["reporter_id"] == str(test_user.id)
        assert data["reviewer_id"] is None
        assert data["reviewed_at"] is None

        # Verify reputation was awarded
        await db_session.refresh(test_user)
        assert test_user.reputation_score == initial_reputation + ReputationReward.REPORT_SUBMITTED

    async def test_create_report_without_description(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test creating a report without optional description."""
        entity_id = str(uuid.uuid4())

        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "album",
                "entity_id": entity_id,
                "field_name": "release_date",
                "current_value": "2020",
                "suggested_value": "2021",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] is None

    async def test_create_report_all_entity_types(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test creating reports for different entity types."""
        entity_types = ["song", "artist", "album", "playlist"]

        for entity_type in entity_types:
            entity_id = str(uuid.uuid4())
            response = await authenticated_client.post(
                "/api/v1/reports",
                json={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "field_name": "name",
                    "current_value": "Old Name",
                    "suggested_value": "New Name",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["entity_type"] == entity_type

    async def test_create_report_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that creating a report requires authentication."""
        response = await client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": str(uuid.uuid4()),
                "field_name": "title",
                "current_value": "Old",
                "suggested_value": "New",
            },
        )

        assert response.status_code == 401

    async def test_create_report_invalid_entity_id(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test creating report with invalid entity ID."""
        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": "not-a-uuid",
                "field_name": "title",
                "current_value": "Old",
                "suggested_value": "New",
            },
        )

        assert response.status_code == 400
        assert "Invalid entity ID" in response.json()["detail"]

    async def test_create_report_missing_required_fields(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test creating report without required fields."""
        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": str(uuid.uuid4()),
                # Missing field_name, current_value, suggested_value
            },
        )

        assert response.status_code == 422

    async def test_create_report_invalid_entity_type(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test creating report with invalid entity type."""
        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "invalid_type",
                "entity_id": str(uuid.uuid4()),
                "field_name": "title",
                "current_value": "Old",
                "suggested_value": "New",
            },
        )

        assert response.status_code == 422


# ====== Report Listing Tests ======


class TestGetMyReports:
    """Tests for GET /api/v1/reports/me."""

    async def test_get_my_reports_success(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_report: MetadataReport,
    ) -> None:
        """Test getting current user's reports."""
        response = await authenticated_client.get("/api/v1/reports/me")

        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] >= 1
        assert len(data["reports"]) >= 1
        assert all(r["reporter_id"] == str(test_user.id) for r in data["reports"])

    async def test_get_my_reports_pagination(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination of user's reports."""
        # Create multiple reports
        for i in range(5):
            report = MetadataReport(
                entity_type=MetadataReportEntityType.SONG.value,
                entity_id=uuid.uuid4(),
                reporter_id=test_user.id,
                field_name=f"field_{i}",
                current_value=f"old_{i}",
                suggested_value=f"new_{i}",
                status=ReportStatus.PENDING.value,
            )
            db_session.add(report)
        await db_session.commit()

        response = await authenticated_client.get(
            "/api/v1/reports/me", params={"page": 1, "page_size": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) <= 3
        assert data["page"] == 1
        assert data["page_size"] == 3

    async def test_get_my_reports_filter_by_status(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test filtering user's reports by status."""
        # Create reports with different statuses
        pending_report = MetadataReport(
            entity_type=MetadataReportEntityType.SONG.value,
            entity_id=uuid.uuid4(),
            reporter_id=test_user.id,
            field_name="pending_field",
            current_value="old",
            suggested_value="new",
            status=ReportStatus.PENDING.value,
        )
        fixed_report = MetadataReport(
            entity_type=MetadataReportEntityType.SONG.value,
            entity_id=uuid.uuid4(),
            reporter_id=test_user.id,
            field_name="fixed_field",
            current_value="old",
            suggested_value="new",
            status=ReportStatus.FIXED.value,
        )
        db_session.add_all([pending_report, fixed_report])
        await db_session.commit()

        response = await authenticated_client.get(
            "/api/v1/reports/me", params={"status": "pending"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(r["status"] == "pending" for r in data["reports"])

    async def test_get_my_reports_empty(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test getting reports when user has no reports."""
        response = await authenticated_client.get("/api/v1/reports/me")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["reports"]) == 0

    async def test_get_my_reports_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that getting reports requires authentication."""
        response = await client.get("/api/v1/reports/me")

        assert response.status_code == 401

    async def test_get_my_reports_ordered_by_date(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test that reports are ordered by creation date descending."""
        # Create multiple reports
        for i in range(3):
            report = MetadataReport(
                entity_type=MetadataReportEntityType.SONG.value,
                entity_id=uuid.uuid4(),
                reporter_id=test_user.id,
                field_name=f"field_{i}",
                current_value=f"old_{i}",
                suggested_value=f"new_{i}",
                status=ReportStatus.PENDING.value,
            )
            db_session.add(report)
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/reports/me")

        assert response.status_code == 200
        data = response.json()
        if len(data["reports"]) > 1:
            dates = [r["created_at"] for r in data["reports"]]
            # Verify descending order
            assert dates == sorted(dates, reverse=True)


# ====== Admin Report Listing Tests ======


class TestListReports:
    """Tests for GET /api/v1/reports (admin)."""

    async def test_list_reports_success(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test admin listing all reports."""
        response = await admin_client.get("/api/v1/reports")

        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] >= 1

    async def test_list_reports_requires_admin(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that non-admin users cannot list all reports."""
        response = await authenticated_client.get("/api/v1/reports")

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    async def test_list_reports_pagination(
        self,
        admin_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination of all reports."""
        # Create multiple reports
        for i in range(5):
            report = MetadataReport(
                entity_type=MetadataReportEntityType.SONG.value,
                entity_id=uuid.uuid4(),
                reporter_id=test_user.id,
                field_name=f"field_{i}",
                current_value=f"old_{i}",
                suggested_value=f"new_{i}",
                status=ReportStatus.PENDING.value,
            )
            db_session.add(report)
        await db_session.commit()

        response = await admin_client.get("/api/v1/reports", params={"page": 1, "page_size": 3})

        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) <= 3
        assert data["page"] == 1
        assert data["page_size"] == 3

    async def test_list_reports_filter_by_status(
        self,
        admin_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test filtering reports by status."""
        # Create reports with different statuses
        for status in [ReportStatus.PENDING, ReportStatus.FIXED, ReportStatus.DISMISSED]:
            report = MetadataReport(
                entity_type=MetadataReportEntityType.SONG.value,
                entity_id=uuid.uuid4(),
                reporter_id=test_user.id,
                field_name=f"field_{status.value}",
                current_value="old",
                suggested_value="new",
                status=status.value,
            )
            db_session.add(report)
        await db_session.commit()

        response = await admin_client.get("/api/v1/reports", params={"status": "fixed"})

        assert response.status_code == 200
        data = response.json()
        assert all(r["status"] == "fixed" for r in data["reports"])

    async def test_list_reports_filter_by_entity_type(
        self,
        admin_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test filtering reports by entity type."""
        # Create reports for different entity types
        for entity_type in [
            MetadataReportEntityType.SONG,
            MetadataReportEntityType.ARTIST,
            MetadataReportEntityType.ALBUM,
        ]:
            report = MetadataReport(
                entity_type=entity_type.value,
                entity_id=uuid.uuid4(),
                reporter_id=test_user.id,
                field_name="name",
                current_value="old",
                suggested_value="new",
                status=ReportStatus.PENDING.value,
            )
            db_session.add(report)
        await db_session.commit()

        response = await admin_client.get("/api/v1/reports", params={"entity_type": "artist"})

        assert response.status_code == 200
        data = response.json()
        assert all(r["entity_type"] == "artist" for r in data["reports"])

    async def test_list_reports_combined_filters(
        self,
        admin_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test combining multiple filters."""
        # Create various reports
        report = MetadataReport(
            entity_type=MetadataReportEntityType.SONG.value,
            entity_id=uuid.uuid4(),
            reporter_id=test_user.id,
            field_name="title",
            current_value="old",
            suggested_value="new",
            status=ReportStatus.PENDING.value,
        )
        db_session.add(report)
        await db_session.commit()

        response = await admin_client.get(
            "/api/v1/reports",
            params={"status": "pending", "entity_type": "song", "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(r["status"] == "pending" and r["entity_type"] == "song" for r in data["reports"])

    async def test_list_reports_includes_usernames(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test that report list includes username relationships."""
        response = await admin_client.get("/api/v1/reports")

        assert response.status_code == 200
        data = response.json()
        if data["reports"]:
            report = data["reports"][0]
            assert "reporter_username" in report
            # reporter_username should be present for reports


# ====== Get Single Report Tests ======


class TestGetReport:
    """Tests for GET /api/v1/reports/{report_id}."""

    async def test_get_report_success_as_owner(
        self,
        authenticated_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test getting a report as the owner."""
        response = await authenticated_client.get(f"/api/v1/reports/{test_report.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_report.id)
        assert data["field_name"] == test_report.field_name
        assert data["current_value"] == test_report.current_value
        assert data["suggested_value"] == test_report.suggested_value

    async def test_get_report_success_as_admin(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test getting any report as admin."""
        response = await admin_client.get(f"/api/v1/reports/{test_report.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_report.id)

    async def test_get_report_forbidden_for_non_owner(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that non-owners cannot view other users' reports."""
        # Create another user and their report
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password="hashed",
        )
        db_session.add(other_user)
        await db_session.commit()

        other_report = MetadataReport(
            entity_type=MetadataReportEntityType.SONG.value,
            entity_id=uuid.uuid4(),
            reporter_id=other_user.id,
            field_name="title",
            current_value="old",
            suggested_value="new",
            status=ReportStatus.PENDING.value,
        )
        db_session.add(other_report)
        await db_session.commit()
        await db_session.refresh(other_report)

        response = await authenticated_client.get(f"/api/v1/reports/{other_report.id}")

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    async def test_get_report_not_found(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test getting non-existent report."""
        fake_id = str(uuid.uuid4())
        response = await authenticated_client.get(f"/api/v1/reports/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_report_invalid_uuid(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test getting report with invalid UUID."""
        response = await authenticated_client.get("/api/v1/reports/invalid-uuid")

        assert response.status_code == 400
        assert "Invalid report ID" in response.json()["detail"]

    async def test_get_report_requires_authentication(
        self,
        client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test that getting a report requires authentication."""
        response = await client.get(f"/api/v1/reports/{test_report.id}")

        assert response.status_code == 401


# ====== Update Report Status Tests ======


class TestUpdateReport:
    """Tests for PATCH /api/v1/reports/{report_id}."""

    async def test_update_report_to_fixed(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test updating report status to fixed."""
        initial_reputation = test_user.reputation_score

        response = await admin_client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "fixed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fixed"
        assert data["reviewer_id"] is not None
        assert data["reviewed_at"] is not None

        # Verify reputation was awarded
        await db_session.refresh(test_user)
        assert test_user.reputation_score == initial_reputation + ReputationReward.REPORT_FIXED

    async def test_update_report_to_reviewed(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test updating report status to reviewed."""
        initial_reputation = test_user.reputation_score

        response = await admin_client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "reviewed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reviewed"

        # Verify reputation was awarded
        await db_session.refresh(test_user)
        assert test_user.reputation_score == initial_reputation + ReputationReward.REPORT_REVIEWED

    async def test_update_report_to_dismissed(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test updating report status to dismissed."""
        # Set initial reputation to ensure it doesn't go negative
        test_user.reputation_score = 100
        await db_session.commit()
        initial_reputation = test_user.reputation_score

        response = await admin_client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "dismissed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"

        # Verify reputation was deducted
        await db_session.refresh(test_user)
        assert test_user.reputation_score == initial_reputation + ReputationReward.REPORT_DISMISSED

    async def test_update_report_sets_reviewer_info(
        self,
        admin_client: AsyncClient,
        admin_user: User,
        test_report: MetadataReport,
        db_session: AsyncSession,
    ) -> None:
        """Test that updating report sets reviewer and timestamp."""
        response = await admin_client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "fixed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reviewer_id"] == str(admin_user.id)
        assert data["reviewed_at"] is not None

        # Verify in database
        await db_session.refresh(test_report)
        assert test_report.reviewed_by == admin_user.id
        assert test_report.reviewed_at is not None

    async def test_update_report_requires_admin(
        self,
        authenticated_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test that non-admin users cannot update reports."""
        response = await authenticated_client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "fixed"},
        )

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    async def test_update_report_not_found(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test updating non-existent report."""
        fake_id = str(uuid.uuid4())
        response = await admin_client.patch(
            f"/api/v1/reports/{fake_id}",
            json={"status": "fixed"},
        )

        assert response.status_code == 404

    async def test_update_report_invalid_uuid(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test updating report with invalid UUID."""
        response = await admin_client.patch(
            "/api/v1/reports/invalid-uuid",
            json={"status": "fixed"},
        )

        assert response.status_code == 400
        assert "Invalid report ID" in response.json()["detail"]

    async def test_update_already_reviewed_report_no_reputation_change(
        self,
        admin_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test that updating already reviewed report doesn't award reputation again."""
        # Create already reviewed report
        report = MetadataReport(
            entity_type=MetadataReportEntityType.SONG.value,
            entity_id=uuid.uuid4(),
            reporter_id=test_user.id,
            field_name="title",
            current_value="old",
            suggested_value="new",
            status=ReportStatus.REVIEWED.value,
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        initial_reputation = test_user.reputation_score

        # Change from reviewed to fixed
        response = await admin_client.patch(
            f"/api/v1/reports/{report.id}",
            json={"status": "fixed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fixed"

        # Reputation should not change (previous_status was not pending)
        await db_session.refresh(test_user)
        assert test_user.reputation_score == initial_reputation

    async def test_update_report_invalid_status(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test updating report with invalid status."""
        response = await admin_client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "invalid_status"},
        )

        assert response.status_code == 422

    async def test_update_report_requires_authentication(
        self,
        client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test that updating a report requires authentication."""
        response = await client.patch(
            f"/api/v1/reports/{test_report.id}",
            json={"status": "fixed"},
        )

        assert response.status_code == 401


# ====== Delete Report Tests ======


class TestDeleteReport:
    """Tests for DELETE /api/v1/reports/{report_id}."""

    async def test_delete_report_success(
        self,
        admin_client: AsyncClient,
        test_report: MetadataReport,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting a report successfully."""
        report_id = test_report.id

        response = await admin_client.delete(f"/api/v1/reports/{report_id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()
        assert data["id"] == str(report_id)

        # Verify report is deleted from database
        result = await db_session.execute(
            select(MetadataReport).where(MetadataReport.id == report_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_report_requires_admin(
        self,
        authenticated_client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test that non-admin users cannot delete reports."""
        response = await authenticated_client.delete(f"/api/v1/reports/{test_report.id}")

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    async def test_delete_report_not_found(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test deleting non-existent report."""
        fake_id = str(uuid.uuid4())
        response = await admin_client.delete(f"/api/v1/reports/{fake_id}")

        assert response.status_code == 404

    async def test_delete_report_invalid_uuid(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test deleting report with invalid UUID."""
        response = await admin_client.delete("/api/v1/reports/invalid-uuid")

        assert response.status_code == 400
        assert "Invalid report ID" in response.json()["detail"]

    async def test_delete_report_requires_authentication(
        self,
        client: AsyncClient,
        test_report: MetadataReport,
    ) -> None:
        """Test that deleting a report requires authentication."""
        response = await client.delete(f"/api/v1/reports/{test_report.id}")

        assert response.status_code == 401


# ====== Edge Cases and Validation Tests ======


class TestReportsEdgeCases:
    """Tests for edge cases and validation scenarios."""

    async def test_create_report_long_field_name(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test creating report with field name at max length."""
        long_field_name = "a" * 100  # Max length is 100

        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": str(uuid.uuid4()),
                "field_name": long_field_name,
                "current_value": "old",
                "suggested_value": "new",
            },
        )

        assert response.status_code == 200

    async def test_create_report_field_name_too_long(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test creating report with field name exceeding max length."""
        too_long_field_name = "a" * 101  # Over max length

        response = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": str(uuid.uuid4()),
                "field_name": too_long_field_name,
                "current_value": "old",
                "suggested_value": "new",
            },
        )

        assert response.status_code == 422

    async def test_pagination_boundary_conditions(
        self,
        admin_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with boundary conditions."""
        # Create exactly 20 reports
        for i in range(20):
            report = MetadataReport(
                entity_type=MetadataReportEntityType.SONG.value,
                entity_id=uuid.uuid4(),
                reporter_id=test_user.id,
                field_name=f"field_{i}",
                current_value=f"old_{i}",
                suggested_value=f"new_{i}",
                status=ReportStatus.PENDING.value,
            )
            db_session.add(report)
        await db_session.commit()

        # Test first page
        response = await admin_client.get("/api/v1/reports", params={"page": 1, "page_size": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) <= 20

        # Test page beyond available data
        response = await admin_client.get("/api/v1/reports", params={"page": 100, "page_size": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) == 0

    async def test_multiple_reports_for_same_entity(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test creating multiple reports for the same entity."""
        entity_id = str(uuid.uuid4())

        # Create first report
        response1 = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": entity_id,
                "field_name": "title",
                "current_value": "Wrong Title",
                "suggested_value": "Correct Title",
            },
        )
        assert response1.status_code == 200

        # Create second report for different field
        response2 = await authenticated_client.post(
            "/api/v1/reports",
            json={
                "entity_type": "song",
                "entity_id": entity_id,
                "field_name": "artist",
                "current_value": "Wrong Artist",
                "suggested_value": "Correct Artist",
            },
        )
        assert response2.status_code == 200

        # Both should succeed
        assert response1.json()["entity_id"] == entity_id
        assert response2.json()["entity_id"] == entity_id

    async def test_empty_pagination_parameters(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test pagination with default parameters."""
        response = await admin_client.get("/api/v1/reports")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20  # Default page size

    async def test_invalid_pagination_parameters(
        self,
        admin_client: AsyncClient,
    ) -> None:
        """Test pagination with invalid parameters."""
        # Page less than 1
        response = await admin_client.get("/api/v1/reports", params={"page": 0})
        assert response.status_code == 422

        # Page size greater than max
        response = await admin_client.get("/api/v1/reports", params={"page_size": 101})
        assert response.status_code == 422

        # Negative page size
        response = await admin_client.get("/api/v1/reports", params={"page_size": -1})
        assert response.status_code == 422
