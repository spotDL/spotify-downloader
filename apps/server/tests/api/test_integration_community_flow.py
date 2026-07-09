"""Plan 6 acceptance test: the offline end-to-end community flow (spec §6.2).

Like Plan 5's ``test_integration_resolve_flow`` this proves the **real boot path**
— a tmp-file SQLite DB migrated by :func:`spotdl_server.bootstrap.upgrade_to_head`
(the same programmatic Alembic seam Plan 8's embedded CLI uses), so migration
``0002`` (the community tables), not ``metadata.create_all``, backs the running
app. The provider registry is faked at the ``create_app(..., registry=...)`` seam
so a canonical track exists to resolve, a :class:`FakeClock` drives token expiry,
and auth is enabled so every community write is exercised over ``ASGITransport``.

The one non-HTTP seam is the vote policy: the default ``VOTE_POLICY_V1`` needs a
``net_score`` of 5 across ≥3 votes to verify a match, but this flow (per the
brief) crosses the threshold with just two upvotes. Since the policy is *injected*
config (not a magic number), the test pins a lower-threshold policy through the
``get_vote_service`` dependency — the same seam a hosted operator would use to
recalibrate — leaving every other route on its real wiring.

The flow, one unit of work per HTTP call:

1. ``POST /auth/register`` → tokens; ``GET /auth/me`` → 200.
2. ``POST /resolve`` a Spotify URL → a canonical track id.
3. ``POST /tracks/{id}/matches`` (Bearer) → 201 community match
   (``matcher_version=community``, ``status=auto``, ``submitted_by`` set in the DB).
4. Two more users upvote → the match crosses the (pinned) threshold and
   ``GET /tracks/{id}/matches`` shows it ``community_verified`` first.
5. One voter retracts → status recomputes back to ``auto``; tallies stay
   consistent (``net_score == upvotes - downvotes``).
6. ``POST /reports`` → pending; a seeded admin approves it; ``GET /admin/stats``
   reflects the counts.
7. ``POST /auth/refresh`` rotates; replaying the spent refresh token → 401
   (family revoked); after ``POST /auth/logout`` a subsequent refresh → 401.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI
from pydantic import SecretStr
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_server.api.deps import get_session, get_vote_service
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.db.models import Match, User
from spotdl_server.policies.voting import VotePolicy
from spotdl_server.repositories.votes import VoteRepository
from spotdl_server.services.voting import VoteService
from spotdl_server.settings import DeploymentMode, Settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.server.tests.conftest import FakeClock
from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeLyricsProvider,
    FakeResolver,
    build_fake_registry,
)

SPOTIFY_URL = "https://open.spotify.com/track/track123"
SUBMIT_URL = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"  # ytmusic — an audio target

TRACK = Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567")

CANDIDATES = (
    AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt-algo",
        url="https://audio/yt-algo",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    ),
)

# The default policy verifies a match at net_score >= 5 over >= 3 votes. This flow
# crosses on two upvotes, so pin a lower-threshold (but structurally identical)
# policy — the injectable-config seam, exercised exactly as a hosted operator would.
_FAST_POLICY = VotePolicy(
    policy_version="vote-integration",
    match_verify_net_score=2,
    match_reject_net_score=-2,
    min_votes_for_status=2,
)


def _fast_vote_service(session: AsyncSession = Depends(get_session)) -> VoteService:  # noqa: B008
    """A ``VoteService`` on the request session but with the low-threshold policy.

    Uses FastAPI's ``Depends`` in a default (the framework's DI idiom, ignored in
    the api layer by config) so the override still shares the request unit of work.
    """
    return VoteService(session=session, votes=VoteRepository(session), policy=_FAST_POLICY)


def _build_registry():  # type: ignore[no-untyped-def]
    return build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=TRACK),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=list(CANDIDATES)),
        FakeLyricsProvider(id=ProviderId.GENIUS, text="la la la"),
    )


@asynccontextmanager
async def _migrated_app(
    data_dir: Path, clock: FakeClock
) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
    """A client + app over a **migrated** tmp-file DB with auth enabled."""
    settings = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        auth_secret_key=SecretStr("integration-secret-key-0123456789-abcdef"),
    )
    # ``upgrade_to_head`` drives Alembic's async env via its own ``asyncio.run``;
    # run it off the test loop so that nested call gets a fresh loop.
    await asyncio.to_thread(upgrade_to_head, settings)  # real boot path — NOT create_all
    app = create_app(settings, registry=_build_registry())
    app.dependency_overrides[get_vote_service] = _fast_vote_service
    async with app.router.lifespan_context(app):
        app.state.clock = clock  # deterministic token expiry
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: httpx.AsyncClient, email: str) -> dict:  # type: ignore[type-arg]
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": email.split("@")[0]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _promote_admin(app: FastAPI, user_id: str) -> None:
    async with app.state.sessionmaker() as db:
        user = await db.get(User, UUID(user_id))
        assert user is not None
        user.is_admin = True
        await db.commit()


async def _match_submitted_by(app: FastAPI, match_id: str) -> UUID | None:
    async with app.state.sessionmaker() as db:
        match = await db.scalar(select(Match).where(Match.id == UUID(match_id)))
        assert match is not None
        return match.submitted_by


async def test_community_flow_end_to_end(tmp_path: Path, clock: FakeClock) -> None:
    async with _migrated_app(tmp_path, clock) as (client, app):
        # 1) The submitter registers and identifies themselves.
        submitter = await _register(client, "submitter@example.com")
        access = submitter["access_token"]
        refresh_original = submitter["refresh_token"]
        submitter_id = submitter["user"]["id"]

        me = await client.get("/api/v1/auth/me", headers=_bearer(access))
        assert me.status_code == 200, me.text
        assert me.json()["email"] == "submitter@example.com"

        # 2) Resolve a Spotify URL → a canonical track id (Plan 5 read path, no auth).
        resolve = await client.post("/api/v1/resolve", json={"query": SPOTIFY_URL})
        assert resolve.status_code == 200, resolve.text
        track_id = resolve.json()["entity"]["track"]["id"]

        # 3) Submit a community audio match for that track.
        submit = await client.post(
            f"/api/v1/tracks/{track_id}/matches",
            json={"url": SUBMIT_URL},
            headers=_bearer(access),
        )
        assert submit.status_code == 201, submit.text
        match = submit.json()
        match_id = match["id"]
        assert match["target_provider"] == "ytmusic"
        assert match["matcher_version"] == "community"
        assert match["status"] == "auto"
        # ``submitted_by`` is provenance, not on the wire shape — assert it in the DB.
        assert await _match_submitted_by(app, match_id) == UUID(submitter_id)

        # 4) Two more users upvote → the match crosses the pinned threshold.
        for email in ("voter-a@example.com", "voter-b@example.com"):
            voter = await _register(client, email)
            vote = await client.post(
                f"/api/v1/matches/{match_id}/vote",
                json={"value": "up"},
                headers=_bearer(voter["access_token"]),
            )
            assert vote.status_code == 200, vote.text
            if email == "voter-a@example.com":
                voter_a_access = voter["access_token"]
        assert vote.json()["status"] == "community_verified"
        assert vote.json()["net_score"] == 2

        # The community match now sorts first (net_score desc) and reads verified.
        listed = (await client.get(f"/api/v1/tracks/{track_id}/matches")).json()["matches"]
        assert listed[0]["id"] == match_id
        assert listed[0]["status"] == "community_verified"
        assert listed[0]["net_score"] == 2

        # 5) One voter retracts → status recomputes back to auto; tallies consistent.
        retract = await client.post(
            f"/api/v1/matches/{match_id}/vote",
            json={"value": "retract"},
            headers=_bearer(voter_a_access),
        )
        assert retract.status_code == 200, retract.text
        body = retract.json()
        assert body["your_vote"] is None
        assert body["status"] == "auto"  # total (1) < min_votes_for_status (2)
        assert body["net_score"] == body["upvotes"] - body["downvotes"] == 1

        # 6) File a metadata-correction report; a seeded admin approves it.
        admin = await _register(client, "admin@example.com")
        await _promote_admin(app, admin["user"]["id"])
        admin_headers = _bearer(admin["access_token"])

        report = await client.post(
            "/api/v1/reports",
            json={
                "subject_type": "track",
                "subject_id": track_id,
                "field": "name",
                "proposed_value": "Corrected Song Title",
                "reason": "the title has a typo",
            },
            headers=_bearer(access),
        )
        assert report.status_code == 201, report.text
        report_id = report.json()["id"]
        assert report.json()["status"] == "pending"

        approve = await client.post(
            f"/api/v1/admin/reports/{report_id}/approve",
            json={"note": "verified against the release"},
            headers=admin_headers,
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["status"] == "approved"

        stats = await client.get("/api/v1/admin/stats", headers=admin_headers)
        assert stats.status_code == 200, stats.text
        counts = stats.json()
        assert counts["users_total"] == 4  # submitter + 2 voters + admin
        assert counts["reports_total"] == 1
        assert counts["reports_pending"] == 0  # the only report was approved
        assert counts["votes_total"] == 1  # two upvotes, one retracted
        assert counts["community_verified_matches"] == 0  # reverted to auto in step 5

        # 7) Refresh rotates the submitter's token; replaying the spent one is 401
        #    (family revoked), and after logout a subsequent refresh is 401 too.
        rotated = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_original}
        )
        assert rotated.status_code == 200, rotated.text
        refresh_rotated = rotated.json()["refresh_token"]
        assert refresh_rotated != refresh_original

        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_original})
        assert replay.status_code == 401
        assert replay.json()["code"] == "invalid_token"

        logout = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_rotated},
            headers=_bearer(access),
        )
        assert logout.status_code == 204, logout.text

        after_logout = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_rotated}
        )
        assert after_logout.status_code == 401
