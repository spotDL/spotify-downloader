"""Plan 6 community-layer schema, mechanically enforced.

Mirror of ``test_models.py`` for the six NEW tables added by Plan 6
(``users``, ``oauth_identities``, ``refresh_tokens``, ``api_tokens``,
``votes``, ``reports``). These tests ARE the §6.1 deferred-set contract:
they assert the exact column list, nullability, defaults, unique/check
constraints, FK ``ondelete`` rules and the polymorphic no-FK guards.

They ALSO pin the additive-only guarantee: the Plan-5 tables
``matches``/``lyrics``/``entity_links`` must be byte-identical to their
Plan-5 column contract (this plan adds tables, never ALTERs one).
"""

from collections.abc import Iterator
from typing import Any

import pytest
from spotdl_core.model import EntityType, MatchStatus
from spotdl_server.db.base import Base
from spotdl_server.db.enums import LinkStatus, OAuthProvider, ReportStatus, VotableType
from spotdl_server.db.models import (
    ApiToken,
    OAuthIdentity,
    RefreshToken,
    Report,
    User,
    Vote,
)
from sqlalchemy import Column, Table, create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# All eleven Plan-5 tables must still be present (no removals).
PLAN5_TABLES = {
    "provider_snapshots",
    "albums",
    "artists",
    "tracks",
    "playlists",
    "track_artists",
    "playlist_tracks",
    "entity_links",
    "matches",
    "lyrics",
    "download_batches",
    "download_jobs",
}
NEW_TABLES = {
    "users",
    "oauth_identities",
    "refresh_tokens",
    "api_tokens",
    "votes",
    "reports",
}
# Tables added by later phases (Phase 1b's ``entity_stat``) — neither Plan-5 nor
# the Plan-6 community layer this module guards, but part of the full metadata.
OTHER_TABLES = {"entity_stat"}


# --------------------------------------------------------------------------- #
# schema descriptor helpers (identical semantics to test_models.py)
# --------------------------------------------------------------------------- #
def _default(col: Column[Any]) -> Any:
    d = col.default
    if d is None:
        return None
    if getattr(d, "is_scalar", False):
        return d.arg
    if getattr(d, "is_callable", False):
        return "callable"
    return repr(getattr(d, "arg", d))


def describe(table: Table) -> dict[str, tuple[str, int | None, bool, Any]]:
    """Map column name -> (type class name, length, nullable, scalar default)."""
    return {
        c.name: (
            type(c.type).__name__,
            getattr(c.type, "length", None),
            c.nullable,
            _default(c),
        )
        for c in table.columns
    }


def tbl(name: str) -> Table:
    return Base.metadata.tables[name]


# --------------------------------------------------------------------------- #
# engine fixture (FK enforcement on for SQLite)
# --------------------------------------------------------------------------- #
@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = create_engine("sqlite://")

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn: Any, _rec: Any) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as s:
        yield s


def _user(session: Session, *, email: str = "a@b.com", is_admin: bool = False) -> User:
    u = User(email=email, is_admin=is_admin)
    session.add(u)
    session.flush()
    return u


# --------------------------------------------------------------------------- #
# table set
# --------------------------------------------------------------------------- #
def test_new_tables_present() -> None:
    tables = set(Base.metadata.tables.keys())
    assert tables >= NEW_TABLES
    # every Plan-5 table still present — no removals.
    assert tables >= PLAN5_TABLES
    assert tables == PLAN5_TABLES | NEW_TABLES | OTHER_TABLES


# --------------------------------------------------------------------------- #
# per-table column contracts
# --------------------------------------------------------------------------- #
def test_users_columns() -> None:
    assert describe(tbl("users")) == {
        "id": ("Uuid", None, False, "callable"),
        "email": ("String", 320, False, None),
        "password_hash": ("String", 255, True, None),
        "display_name": ("String", 255, True, None),
        "is_admin": ("Boolean", None, False, False),
        "is_active": ("Boolean", None, False, True),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_oauth_identities_columns() -> None:
    assert describe(tbl("oauth_identities")) == {
        "id": ("Uuid", None, False, "callable"),
        "user_id": ("Uuid", None, False, None),
        "provider": ("Enum", 32, False, None),
        "provider_account_id": ("String", 255, False, None),
        "provider_username": ("String", 255, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_refresh_tokens_columns() -> None:
    assert describe(tbl("refresh_tokens")) == {
        "id": ("Uuid", None, False, "callable"),
        "user_id": ("Uuid", None, False, None),
        "token_hash": ("String", 64, False, None),
        "family_id": ("Uuid", None, False, None),
        "issued_at": ("DateTime", None, False, "callable"),
        "expires_at": ("DateTime", None, False, None),
        "rotated_at": ("DateTime", None, True, None),
        "revoked_at": ("DateTime", None, True, None),
        "replaced_by": ("Uuid", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_api_tokens_columns() -> None:
    assert describe(tbl("api_tokens")) == {
        "id": ("Uuid", None, False, "callable"),
        "user_id": ("Uuid", None, False, None),
        "name": ("String", 255, False, None),
        "token_prefix": ("String", 24, False, None),
        "token_hash": ("String", 64, False, None),
        "last_used_at": ("DateTime", None, True, None),
        "expires_at": ("DateTime", None, True, None),
        "revoked_at": ("DateTime", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_votes_columns() -> None:
    assert describe(tbl("votes")) == {
        "id": ("Uuid", None, False, "callable"),
        "user_id": ("Uuid", None, False, None),
        "votable_type": ("Enum", 32, False, None),
        "votable_id": ("Uuid", None, False, None),
        "value": ("Integer", None, False, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


def test_reports_columns() -> None:
    assert describe(tbl("reports")) == {
        "id": ("Uuid", None, False, "callable"),
        "reporter_id": ("Uuid", None, True, None),
        "subject_type": ("Enum", 32, False, None),
        "subject_id": ("Uuid", None, False, None),
        "field": ("String", 64, True, None),
        "proposed_value": ("Text", None, True, None),
        "reason": ("Text", None, True, None),
        "status": ("Enum", 32, False, ReportStatus.PENDING),
        "reviewed_by": ("Uuid", None, True, None),
        "reviewed_at": ("DateTime", None, True, None),
        "review_note": ("Text", None, True, None),
        "created_at": ("DateTime", None, False, "callable"),
        "updated_at": ("DateTime", None, False, "callable"),
    }


# --------------------------------------------------------------------------- #
# indexes present per contract
# --------------------------------------------------------------------------- #
def test_expected_indexes_present() -> None:
    def ix_names(name: str) -> set[str]:
        return {ix.name for ix in tbl(name).indexes if ix.name}

    assert "ix_oauth_identities_user_id" in ix_names("oauth_identities")
    assert {"ix_refresh_tokens_user_id", "ix_refresh_tokens_family_id"} <= ix_names(
        "refresh_tokens"
    )
    assert {"ix_api_tokens_user_id", "ix_api_tokens_token_prefix"} <= ix_names("api_tokens")
    assert "ix_votes_votable_type_votable_id" in ix_names("votes")
    assert {
        "ix_reports_status",
        "ix_reports_subject_type_subject_id",
        "ix_reports_reporter_id",
    } <= ix_names("reports")


# --------------------------------------------------------------------------- #
# unique / check constraints
# --------------------------------------------------------------------------- #
def test_users_email_unique(session: Session) -> None:
    uq_names = {c.name for c in tbl("users").constraints if c.name}
    assert "uq_users_email" in uq_names

    session.add(User(email="dup@x.com"))
    session.commit()
    session.add(User(email="dup@x.com"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_oauth_identity_unique_constraints(session: Session) -> None:
    uq_names = {c.name for c in tbl("oauth_identities").constraints if c.name}
    assert "uq_oauth_identities_provider_provider_account_id" in uq_names
    assert "uq_oauth_identities_user_id_provider" in uq_names

    u1 = _user(session, email="u1@x.com")
    u2 = _user(session, email="u2@x.com")
    session.add(
        OAuthIdentity(
            user_id=u1.id,
            provider=OAuthProvider.GITHUB,
            provider_account_id="gh-1",
        )
    )
    session.commit()
    # same (provider, provider_account_id) on a different user -> IntegrityError
    session.add(
        OAuthIdentity(
            user_id=u2.id,
            provider=OAuthProvider.GITHUB,
            provider_account_id="gh-1",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_oauth_identity_one_per_provider_per_user(session: Session) -> None:
    u = _user(session)
    session.add(
        OAuthIdentity(
            user_id=u.id,
            provider=OAuthProvider.DISCORD,
            provider_account_id="d-1",
        )
    )
    session.commit()
    session.add(
        OAuthIdentity(
            user_id=u.id,
            provider=OAuthProvider.DISCORD,
            provider_account_id="d-2",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_refresh_token_hash_unique(session: Session) -> None:
    uq_names = {c.name for c in tbl("refresh_tokens").constraints if c.name}
    assert "uq_refresh_tokens_token_hash" in uq_names

    import uuid
    from datetime import UTC, datetime

    u = _user(session)
    fam = uuid.uuid4()
    exp = datetime(2030, 1, 1, tzinfo=UTC)
    session.add(RefreshToken(user_id=u.id, token_hash="h" * 64, family_id=fam, expires_at=exp))
    session.commit()
    session.add(RefreshToken(user_id=u.id, token_hash="h" * 64, family_id=fam, expires_at=exp))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_api_token_hash_unique(session: Session) -> None:
    uq_names = {c.name for c in tbl("api_tokens").constraints if c.name}
    assert "uq_api_tokens_token_hash" in uq_names

    u = _user(session)
    session.add(
        ApiToken(user_id=u.id, name="cli", token_prefix="spdl_pat_abcdef", token_hash="t" * 64)
    )
    session.commit()
    session.add(
        ApiToken(user_id=u.id, name="cli2", token_prefix="spdl_pat_ghijkl", token_hash="t" * 64)
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_votes_unique_and_check(session: Session) -> None:
    import uuid

    uq_names = {c.name for c in tbl("votes").constraints if c.name}
    ck_names = {c.name for c in tbl("votes").constraints if c.name}
    assert "uq_votes_user_id_votable_type_votable_id" in uq_names
    assert "ck_votes_value_in_range" in ck_names

    u = _user(session)
    votable = uuid.uuid4()
    session.add(Vote(user_id=u.id, votable_type=VotableType.MATCH, votable_id=votable, value=1))
    session.commit()
    # duplicate (user, type, id) -> IntegrityError
    session.add(Vote(user_id=u.id, votable_type=VotableType.MATCH, votable_id=votable, value=-1))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("bad", [0, 2, -2])
def test_votes_value_check_rejects(session: Session, bad: int) -> None:
    import uuid

    u = _user(session)
    session.add(
        Vote(
            user_id=u.id,
            votable_type=VotableType.LYRICS,
            votable_id=uuid.uuid4(),
            value=bad,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("good", [1, -1])
def test_votes_value_check_accepts(session: Session, good: int) -> None:
    import uuid

    u = _user(session)
    session.add(
        Vote(
            user_id=u.id,
            votable_type=VotableType.ENTITY_LINK,
            votable_id=uuid.uuid4(),
            value=good,
        )
    )
    session.commit()


# --------------------------------------------------------------------------- #
# enum columns — non-native VARCHAR + round trip
# --------------------------------------------------------------------------- #
def test_new_enum_columns_non_native_varchar(session: Session) -> None:
    import uuid

    for name, col in (
        ("oauth_identities", "provider"),
        ("votes", "votable_type"),
        ("reports", "status"),
        ("reports", "subject_type"),
    ):
        assert tbl(name).columns[col].type.native_enum is False  # type: ignore[attr-defined]

    u = _user(session)
    ident = OAuthIdentity(user_id=u.id, provider=OAuthProvider.GITHUB, provider_account_id="gh-x")
    vote = Vote(user_id=u.id, votable_type=VotableType.MATCH, votable_id=uuid.uuid4(), value=1)
    report = Report(
        reporter_id=u.id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        status=ReportStatus.PENDING,
    )
    session.add_all([ident, vote, report])
    session.commit()

    assert ident.provider is OAuthProvider.GITHUB
    assert vote.votable_type is VotableType.MATCH
    assert report.status is ReportStatus.PENDING
    assert report.subject_type is EntityType.TRACK


def test_reports_status_default(session: Session) -> None:
    import uuid

    u = _user(session)
    report = Report(reporter_id=u.id, subject_type=EntityType.ALBUM, subject_id=uuid.uuid4())
    session.add(report)
    session.commit()
    session.refresh(report)
    assert report.status is ReportStatus.PENDING


# --------------------------------------------------------------------------- #
# FK ondelete rules
# --------------------------------------------------------------------------- #
def test_fk_ondelete_rules() -> None:
    for name, col in (
        ("oauth_identities", "user_id"),
        ("refresh_tokens", "user_id"),
        ("api_tokens", "user_id"),
        ("votes", "user_id"),
    ):
        fks = list(tbl(name).columns[col].foreign_keys)
        assert len(fks) == 1
        assert fks[0].column is tbl("users").columns["id"]
        assert fks[0].ondelete == "CASCADE"

    for col in ("reporter_id", "reviewed_by"):
        fks = list(tbl("reports").columns[col].foreign_keys)
        assert len(fks) == 1
        assert fks[0].column is tbl("users").columns["id"]
        assert fks[0].ondelete == "SET NULL"


def test_user_delete_cascades_and_nulls_reports(session: Session) -> None:
    import uuid
    from datetime import UTC, datetime

    admin = _user(session, email="admin@x.com", is_admin=True)
    victim = _user(session, email="victim@x.com")

    session.add_all(
        [
            OAuthIdentity(
                user_id=victim.id,
                provider=OAuthProvider.GITHUB,
                provider_account_id="gh-v",
            ),
            RefreshToken(
                user_id=victim.id,
                token_hash="r" * 64,
                family_id=uuid.uuid4(),
                expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            ),
            ApiToken(
                user_id=victim.id,
                name="cli",
                token_prefix="spdl_pat_zzzzzz",
                token_hash="p" * 64,
            ),
            Vote(
                user_id=victim.id,
                votable_type=VotableType.MATCH,
                votable_id=uuid.uuid4(),
                value=1,
            ),
            # report authored by victim, reviewed by admin
            Report(
                reporter_id=victim.id,
                subject_type=EntityType.TRACK,
                subject_id=uuid.uuid4(),
                reviewed_by=admin.id,
            ),
        ]
    )
    session.commit()
    vid = victim.id

    session.delete(victim)
    session.commit()

    # cascaded rows gone
    for model, col in (
        (OAuthIdentity, OAuthIdentity.user_id),
        (RefreshToken, RefreshToken.user_id),
        (ApiToken, ApiToken.user_id),
        (Vote, Vote.user_id),
    ):
        assert session.execute(select(model).where(col == vid)).all() == []

    # report kept, reporter_id nulled
    report = session.execute(select(Report)).scalar_one()
    assert report.reporter_id is None
    assert report.reviewed_by == admin.id


def test_reviewer_delete_sets_null(session: Session) -> None:
    import uuid

    admin = _user(session, email="admin2@x.com", is_admin=True)
    reporter = _user(session, email="rep@x.com")
    report = Report(
        reporter_id=reporter.id,
        subject_type=EntityType.TRACK,
        subject_id=uuid.uuid4(),
        reviewed_by=admin.id,
    )
    session.add(report)
    session.commit()

    session.delete(admin)
    session.commit()
    session.refresh(report)
    assert report.reviewed_by is None
    assert report.reporter_id == reporter.id


# --------------------------------------------------------------------------- #
# polymorphic no-FK guards
# --------------------------------------------------------------------------- #
def test_votes_have_no_votable_fk() -> None:
    col = tbl("votes").columns["votable_id"]
    assert col.foreign_keys == set()
    assert type(col.type).__name__ == "Uuid"
    assert col.nullable is False


def test_reports_have_no_subject_fk() -> None:
    col = tbl("reports").columns["subject_id"]
    assert col.foreign_keys == set()
    assert type(col.type).__name__ == "Uuid"
    assert col.nullable is False


def test_refresh_token_replaced_by_has_no_fk() -> None:
    # audit-only self-reference; no FK per contract (one insert path).
    col = tbl("refresh_tokens").columns["replaced_by"]
    assert col.foreign_keys == set()
    assert type(col.type).__name__ == "Uuid"
    assert col.nullable is True


# --------------------------------------------------------------------------- #
# additive-only: Plan-5 votable tables byte-identical to their contract
# --------------------------------------------------------------------------- #
# Re-declared byte-for-byte from Plan 5's ``test_models.py`` (test_matches_columns,
# test_lyrics_columns, test_entity_links_columns). Proves 0002 is additive-only.
PLAN5_MATCHES_COLUMNS = {
    "id": ("Uuid", None, False, "callable"),
    "track_id": ("Uuid", None, False, None),
    "target_provider": ("Enum", 32, False, None),
    "target_id": ("String", 512, False, None),
    "target_url": ("String", 2048, False, None),
    "score": ("Float", None, False, None),
    "matcher_version": ("String", 32, False, None),
    "status": ("Enum", 32, False, MatchStatus.AUTO),
    "features": ("JSON", None, True, None),
    "candidate_name": ("String", 1024, True, None),
    "candidate_artists": ("JSON", None, True, None),
    "candidate_duration_ms": ("Integer", None, True, None),
    "submitted_by": ("Uuid", None, True, None),
    "upvotes": ("Integer", None, False, 0),
    "downvotes": ("Integer", None, False, 0),
    "net_score": ("Integer", None, False, 0),
    "created_at": ("DateTime", None, False, "callable"),
    "updated_at": ("DateTime", None, False, "callable"),
}
PLAN5_LYRICS_COLUMNS = {
    "id": ("Uuid", None, False, "callable"),
    "track_id": ("Uuid", None, False, None),
    "source": ("Enum", 32, False, None),
    "kind": ("Enum", 32, False, None),
    "text": ("Text", None, False, None),
    "submitted_by": ("Uuid", None, True, None),
    "upvotes": ("Integer", None, False, 0),
    "downvotes": ("Integer", None, False, 0),
    "net_score": ("Integer", None, False, 0),
    "created_at": ("DateTime", None, False, "callable"),
    "updated_at": ("DateTime", None, False, "callable"),
}
PLAN5_ENTITY_LINKS_COLUMNS = {
    "id": ("Uuid", None, False, "callable"),
    "entity_type": ("Enum", 32, False, None),
    "entity_id": ("Uuid", None, False, None),
    "snapshot_id": ("Uuid", None, False, None),
    "status": ("Enum", 32, False, LinkStatus.AUTO),
    "upvotes": ("Integer", None, False, 0),
    "downvotes": ("Integer", None, False, 0),
    "net_score": ("Integer", None, False, 0),
    "created_at": ("DateTime", None, False, "callable"),
    "updated_at": ("DateTime", None, False, "callable"),
}


def test_no_plan5_table_altered() -> None:
    assert describe(tbl("matches")) == PLAN5_MATCHES_COLUMNS
    assert describe(tbl("lyrics")) == PLAN5_LYRICS_COLUMNS
    assert describe(tbl("entity_links")) == PLAN5_ENTITY_LINKS_COLUMNS


# --------------------------------------------------------------------------- #
# relationships (optional, selectin) — User -> oauth_identities / api_tokens
# --------------------------------------------------------------------------- #
def test_user_relationships_load(session: Session) -> None:
    u = _user(session)
    session.add_all(
        [
            OAuthIdentity(user_id=u.id, provider=OAuthProvider.GITHUB, provider_account_id="gh-r"),
            ApiToken(
                user_id=u.id,
                name="cli",
                token_prefix="spdl_pat_rrrrrr",
                token_hash="q" * 64,
            ),
        ]
    )
    session.commit()
    session.refresh(u)
    assert len(u.oauth_identities) == 1
    assert len(u.api_tokens) == 1
