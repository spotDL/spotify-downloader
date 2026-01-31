"""Tests for votes API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from spotdl.db.models.match import Match as MatchModel
from spotdl.db.models.user import User


pytestmark = pytest.mark.asyncio


class TestVotesEndpoints:
    """Tests for votes API endpoints."""

    async def test_cast_vote_up(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test casting an upvote."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": str(test_match.id), "vote_type": "up"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == str(test_match.id)
        assert data["upvotes"] == 1
        assert data["downvotes"] == 0
        assert data["user_vote"] == "up"

    async def test_cast_vote_down(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test casting a downvote."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": str(test_match.id), "vote_type": "down"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == str(test_match.id)
        assert data["upvotes"] == 0
        assert data["downvotes"] == 1
        assert data["user_vote"] == "down"

    async def test_cast_vote_invalid_type(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test casting vote with invalid type."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": str(test_match.id), "vote_type": "invalid"},
        )

        assert response.status_code == 400

    async def test_cast_vote_invalid_match_id(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test casting vote with invalid match ID."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": "not-a-uuid", "vote_type": "up"},
        )

        assert response.status_code == 422

    async def test_cast_vote_nonexistent_match(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test casting vote for non-existent match."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": str(uuid.uuid4()), "vote_type": "up"},
        )

        assert response.status_code == 404

    async def test_remove_vote(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test removing a vote."""
        # First cast a vote
        await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": str(test_match.id), "vote_type": "up"},
        )

        # Then remove it
        response = await authenticated_client.delete(f"/api/v1/votes/{test_match.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == str(test_match.id)
        assert data["user_vote"] is None

    async def test_get_vote_summary(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test getting vote summary."""
        response = await authenticated_client.get(f"/api/v1/votes/{test_match.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["match_id"] == str(test_match.id)
        assert "upvotes" in data
        assert "downvotes" in data
        assert "score" in data
        assert "total_votes" in data
        assert "confidence" in data

    async def test_get_my_votes(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test getting current user's votes."""
        response = await authenticated_client.get("/api/v1/votes/user/me")

        assert response.status_code == 200
        data = response.json()
        assert "votes" in data
        assert isinstance(data["votes"], list)


    async def test_remove_vote_nonexistent_match(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test removing vote from non-existent match."""
        response = await authenticated_client.delete(f"/api/v1/votes/{uuid.uuid4()}")

        assert response.status_code == 404

    async def test_get_vote_summary_nonexistent_match(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test getting vote summary for non-existent match."""
        response = await authenticated_client.get(f"/api/v1/votes/{uuid.uuid4()}")

        assert response.status_code == 404


class TestVotesValidation:
    """Tests for votes validation."""

    async def test_cast_vote_missing_match_id(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
    ) -> None:
        """Test casting vote without match_id."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"vote_type": "up"},
        )

        assert response.status_code == 422

    async def test_cast_vote_missing_vote_type(
        self,
        authenticated_client: AsyncClient,
        test_user: User,
        test_match: MatchModel,
    ) -> None:
        """Test casting vote without vote_type."""
        response = await authenticated_client.post(
            "/api/v1/votes",
            json={"match_id": str(test_match.id)},
        )

        assert response.status_code == 422
