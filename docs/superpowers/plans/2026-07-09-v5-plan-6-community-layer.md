# spotDL v5 `apps/server` Community Layer Implementation Plan (Plan 6 of 11)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the server community layer on top of Plan 5's metadata backend — the deferred §6.1 tables (`users`, `oauth_identities`, `refresh_tokens`, `api_tokens`, `votes`, `reports`), the §6.2 auth/vote/submit/report/admin endpoints, and §6.4 rate limiting. Implements the §2 decision-record rows for **Auth** (anonymous read with per-IP limits; accounts via email+password and GitHub/Discord OAuth; PATs for CLI) and **Voting scope** (matches, lyrics, metadata corrections, cross-provider entity links). All six new tables are **additive** — this plan adds tables and NEVER `ALTER`s a Plan 5 table (verified below). Downloads/WebSocket remain **Plan 7**.

**Architecture:** Same strict layering as Plan 5: `api.routers` (HTTP only, ≤200 lines each, no business logic, no ORM import) → `services` (orchestration; no FastAPI or SQLAlchemy types in public signatures) → `repositories` (DB only; sole holders of ORM query code) → `db`. Three new **leaf utility packages** sit below `services` and are importable by both `services` and `api` without a layering violation: `spotdl_server.auth` (pure crypto: password hashing, token minting/verification, `AuthContext`, `Clock`, OAuth provider clients), `spotdl_server.ratelimit` (limiter interface + backends). The FastAPI auth dependency and the rate-limit middleware are HTTP glue in `api/`. No module-level mutable singletons: the rate-limit backend and `Clock` are built in the FastAPI lifespan, stored on `app.state`, injected via dependencies, closed on shutdown (mirroring Plan 5's engine/registry wiring). Deployment-mode / feature gating is startup-time (routers mounted or not; rate-limit middleware added or not), never per-request conditionals.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 async ORM, Alembic, Pydantic v2 + pydantic-settings, aiosqlite (default) / asyncpg (optional). New: **PyJWT** (JWT access tokens), **argon2-cffi** (argon2id password hashing), **httpx** (OAuth provider calls — already a server-transitive dep via FastAPI's test client; declared explicitly), optional **redis** (async) behind a `redis` extra. Tests: pytest + pytest-asyncio, httpx `ASGITransport`, **respx** (already in the dev group) for faked OAuth provider HTTP, in-memory + tmp-file SQLite. The default suite is **fully offline**: no real GitHub/Discord, no real Redis, time controlled by an injectable `Clock`.

## Global Constraints

- Python `>=3.13`; single uv lockfile at the workspace root.
- All v5 work happens in the worktree `~/Projects/xnetcat/spotdl-v5` on orphan branch `v5`. Run all commands from that directory unless a step says otherwise.
- Dependency direction (spec §3, machine-enforced by import-linter): `core ← server ← cli`. `spotdl_server` may import `spotdl_core`; it must **never** import `spotdl_cli`.
- New runtime dependencies go in `apps/server/pyproject.toml`; new test-only dependencies go in the root `pyproject.toml` `[dependency-groups].dev`. Exact version floors are given per task.
- No code is copied from the `xnetcat-rewrite` branch or v4. The reference auth (`backend/src/spotdl/core/security.py`, `api/v1/auth.py`) is a **shape reference only**; v5 is deliberately simpler — see "Scope discipline vs the reference branch" below.
- **No module-level mutable singletons.** The `Clock` and the rate-limit backend live on `app.state`, built in the lifespan, closed on shutdown. Services and the auth dependency receive collaborators by dependency injection.
- **Layering is a contract, not a convention** (Task 12): routers import only `fastapi`, Pydantic API schemas, service classes, and `spotdl_server.auth` value types (`AuthContext`) — never `sqlalchemy` or ORM models. Services import repositories, core, and `spotdl_server.auth`/`ratelimit` — never `fastapi`. Repositories are the only modules importing `sqlalchemy`/ORM. Routers stay ≤200 lines.
- TDD: every task writes failing tests first (RED), then implements to green. The default suite is **offline** — no real provider network, no real Postgres, no real Redis required.
- All test directories are packages (`__init__.py`); pytest runs with `--import-mode=importlib`. `apps/server/tests/conftest.py` already strips `SPOTDL_`-prefixed env vars.
- `make check` (lint + typecheck + test + web-check) must pass at the end of **every** task. `make check` runs `pytest -m 'not network'`; Postgres tests stay gated by the `postgres` marker/skip from Plan 5.
- Every commit message ends with:
  `Claude-Session: https://claude.ai/code/session_011axzuDoTDF3K9WhhHbRc5f`

## What already exists (Plan 5 substrate — do not recreate)

- **Schema & DB plumbing:** `db/base.py` (`Base` with `NAMING_CONVENTION` metadata, `TimestampMixin`), `db/engine.py` (`build_engine`/`build_sessionmaker`), `db/enums.py` (`LinkStatus`, `DownloadStatus`), `db/models.py` (all eleven Plan-5 tables). Alembic dual-dialect env with `render_as_batch` on SQLite; migration `0001_initial_schema.py` (`down_revision = None`); `test_migrations.py` autogenerate-parity guard.
- **Votable substrate (verified against `plan-5-draft.md`):** `matches`, `lyrics`, `entity_links` each already carry `upvotes`, `downvotes`, `net_score` (`INTEGER NOT NULL DEFAULT 0`). `matches.submitted_by`, `lyrics.submitted_by`, `download_jobs.requested_by` are **plain nullable `Uuid` columns with NO ForeignKey** (Plan 5 `test_no_user_fk_on_votable_tables` pins this). `matches.status` is `Enum(MatchStatus)` = `auto | community_verified | rejected`; `entity_links.status` is `Enum(LinkStatus)` = `auto | verified | disputed`. **Consequence: this plan adds only NEW tables and NEW-table migrations; it never `ALTER`s a Plan 5 table.**
- **Error envelope (Task 7, Plan 5):** `api/errors.py` `ErrorEnvelope{code, message, detail}`, `ErrorCode` StrEnum (includes `RATE_LIMITED = "rate_limited"`, `VALIDATION_ERROR`, `NOT_FOUND`, `UNSUPPORTED_URL`, `INTERNAL_ERROR`), `register_exception_handlers(app)` with a table-driven `_status_and_code`. `services/errors.py` `NotFoundError(entity_type, entity_id)`. `RateLimited` already maps to HTTP 429 with `Retry-After` — this plan reuses `ErrorCode.RATE_LIMITED` for the limiter and adds new codes for auth/vote/report failures.
- **Config & routing:** `api/schemas.py` (`ConfigResponse{mode, features, matcher_version}`, `FeatureFlags{downloads, auth, voting, library}` — `auth`/`voting` currently hardcoded `False` "until Plan 6"). `meta.py` router serves `GET /config`. `app.py` `create_app(settings)` with lifespan building engine/sessionmaker/registry on `app.state`. `api/deps.py` (`get_sessionmaker`, `get_registry`, `get_session`). `scripts/export_openapi.py` + committed `openapi.json` + `test_openapi.py` in-sync test + `make openapi` target.
- **Settings:** `Settings(BaseSettings, env_prefix="SPOTDL_")` with `mode: DeploymentMode` (`HOSTED|SELFHOST|EMBEDDED`), `data_dir`, `database_url`, `db_echo`, `effective_database_url()`.
- **Core (via Plan 2/3 seams):** `from spotdl_core.providers import parse, UnsupportedURL, PlatformRef, ProviderId`; `PlatformRef(provider, entity_type, entity_id, url)`. `from spotdl_core.model import EntityType, ProviderId, MatchStatus, LyricsKind`.

## Plan series roadmap (context — not part of this plan)

Plan 1 bootstrap → Plan 2 providers → Plan 3 matching → Plan 4 download → Plan 5 server foundation → **Plan 6 auth + community (this plan)** → Plan 7 downloads + WS → Plan 8 clients + CLI → Plan 9 TUI → Plan 10 web → Plan 11 deploy. `GET /metrics` (Prometheus) is observability and belongs to **Plan 11**; this plan ships `GET /admin/stats` (JSON, for the admin UI), which is a different endpoint.

## Scope discipline vs the reference branch

The `xnetcat-rewrite` `security.py` carried a full **JWT-both-tokens + persistent token blacklist + in-memory blacklist cache with DB reconciliation** (`TokenBlacklistCache`, `is_token_blacklisted`, `blacklist_token`, `initialize_token_blacklist`). v5 deliberately drops the blacklist entirely:

| Reference branch | v5 (this plan) | Why simpler |
|---|---|---|
| Refresh token = JWT (stateless, must blacklist to revoke) | Refresh token = **opaque random string, stored hashed in `refresh_tokens`** | Revocation is a DB row update; no blacklist table/cache needed |
| Access + refresh both blacklisted on logout; DB + in-memory cache kept in sync | **No blacklist at all.** Logout revokes the refresh-token family; the 15-minute access token simply expires | Removes the entire `TokenBlacklistCache` machinery and its startup reconciliation |
| bcrypt | **argon2id** (argon2-cffi) | Modern default; memory-hard |
| python-jose (`jose`) | **PyJWT** | Maintained, smaller surface, no JWE we don't use (see Task 3 justification) |
| Username + email + password | **email + password** (email is the identity), display name optional | Matches §2 "email+password" |

Net effect: no `token_blacklist` table, no cache singleton, no `initialize_token_blacklist` on startup. Short access-token lifetime + rotating opaque refresh tokens deliver revocation with less code.

---

## THE NEW TABLES (spec §6.1 deferred set) — authoritative contract

Single source of truth for Task 1 (ORM) and Task 2 (migration `0002`). Cross-dialect rules are **identical to Plan 5** (non-negotiable): UUID PKs `sa.Uuid(as_uuid=True)` Python-side `default=uuid.uuid4`; enums `sa.Enum(PyEnum, native_enum=False, validate_strings=True, length=32)` → VARCHAR+CHECK on both dialects; timestamps via `TimestampMixin` (`created_at`/`updated_at`, tz-aware, Python-side `default`/`onupdate`); `MetaData(naming_convention=...)` already on `Base`; JSON only where noted. All FKs use the naming convention. **Every column below has a stated type, nullability, default, and constraint.**

New server-only DB enums (append to `db/enums.py`):
```python
class OAuthProvider(StrEnum):
    GITHUB = "github"; DISCORD = "discord"
class VotableType(StrEnum):
    MATCH = "match"; LYRICS = "lyrics"; ENTITY_LINK = "entity_link"
class ReportStatus(StrEnum):
    PENDING = "pending"; APPROVED = "approved"; REJECTED = "rejected"
```
`ReportStatus` values map 1:1 to the §6.1 "minimal review state". Report *subject* typing reuses `spotdl_core.model.EntityType` (no new enum). `VotableType` values are the string form of `votes.votable_type`, and their `votable_id` targets are `matches.id` / `lyrics.id` / `entity_links.id` respectively (polymorphic; see the no-FK note).

### Table: `users`
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `email` | String(320) | no | | **normalized** form (see email-normalization contract); the login identity |
| `password_hash` | String(255) | yes | | argon2id encoded hash; **NULL for OAuth-only accounts** |
| `display_name` | String(255) | yes | | optional profile name |
| `is_admin` | Boolean | no | `False` | admin role (guard dependency) |
| `is_active` | Boolean | no | `True` | set `False` to disable/ban (minimal admin) |
| `created_at`/`updated_at` | DateTime(tz) | no | now | TimestampMixin |

Constraints/indexes: `UNIQUE (email)` → `uq_users_email`.

### Table: `oauth_identities`
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `user_id` | Uuid FK→users.id | no | | `ondelete=CASCADE` |
| `provider` | Enum(OAuthProvider) | no | | `github \| discord` |
| `provider_account_id` | String(255) | no | | the provider's stable user id |
| `provider_username` | String(255) | yes | | provider handle, for display |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (provider, provider_account_id)` → `uq_oauth_identities_provider_provider_account_id` (login lookup key); `UNIQUE (user_id, provider)` → `uq_oauth_identities_user_id_provider` (at most one identity per provider per user); `INDEX (user_id)`.

### Table: `refresh_tokens`
Rotating refresh tokens with family-based reuse detection. **Opaque** tokens, stored hashed.
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `user_id` | Uuid FK→users.id | no | | `ondelete=CASCADE`, indexed |
| `token_hash` | String(64) | no | | **sha256 hex** of the opaque token (never store the token) |
| `family_id` | Uuid | no | | rotation lineage; reuse revokes the whole family |
| `issued_at` | DateTime(tz) | no | now | |
| `expires_at` | DateTime(tz) | no | | issued_at + refresh lifetime |
| `rotated_at` | DateTime(tz) | yes | | set when this token is consumed by a refresh (spent) |
| `revoked_at` | DateTime(tz) | yes | | set on logout or reuse-triggered family revoke |
| `replaced_by` | Uuid | yes | | id of the successor token (audit trail; no FK — self-reference avoided to keep one insert path) |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (token_hash)` → `uq_refresh_tokens_token_hash`; `INDEX (user_id)`; `INDEX (family_id)`.

### Table: `api_tokens`
Personal access tokens (PATs) for the CLI. Stored hashed; full token shown once.
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `user_id` | Uuid FK→users.id | no | | `ondelete=CASCADE`, indexed |
| `name` | String(255) | no | | user-supplied label |
| `token_prefix` | String(24) | no | | `spdl_pat_` + first 6 chars of the secret, for identification in listings |
| `token_hash` | String(64) | no | | sha256 hex of the full token |
| `last_used_at` | DateTime(tz) | yes | | updated on successful PAT auth (best-effort) |
| `expires_at` | DateTime(tz) | yes | | NULL = never expires |
| `revoked_at` | DateTime(tz) | yes | | revoke without delete (keeps `last_used_at` audit) |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (token_hash)` → `uq_api_tokens_token_hash`; `INDEX (user_id)`; `INDEX (token_prefix)`.

### Table: `votes`
The vote ledger — one row per (user, votable). §6.1: `(user_id, votable_type, votable_id, value)`, unique per user per object.
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `user_id` | Uuid FK→users.id | no | | `ondelete=CASCADE` |
| `votable_type` | Enum(VotableType) | no | | `match \| lyrics \| entity_link` |
| `votable_id` | Uuid | no | | **polymorphic id** into matches/lyrics/entity_links; **no cross-table FK** |
| `value` | Integer | no | | `+1` (up) or `-1` (down); `CHECK value IN (-1, 1)` → `ck_votes_value_in_range` |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `UNIQUE (user_id, votable_type, votable_id)` → `uq_votes_user_id_votable_type_votable_id` (one vote per user per object; also the race guard); `INDEX (votable_type, votable_id)`.

> **Polymorphic `votable_id` (CONTRACT).** Like Plan 5's `entity_links.entity_id`, `votes.votable_id` is a bounded polymorphic reference disambiguated by `votable_type` — no cross-table FK. `votes.user_id` **is** a real FK into `users` (this table is new, so the FK is additive — no ALTER). Retraction **deletes** the row (see the vote state machine), so there is no `is_retracted` column.

### Table: `reports`
Metadata-correction reports (§6.1 "metadata-correction reports + minimal review state").
| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | Uuid | no | uuid4 | PK |
| `reporter_id` | Uuid FK→users.id | yes | | `ondelete=SET NULL` (keep the report if the user is deleted) |
| `subject_type` | Enum(EntityType) | no | | which canonical entity the correction targets |
| `subject_id` | Uuid | no | | canonical entity id (polymorphic; no cross-table FK) |
| `field` | String(64) | yes | | the field being corrected (e.g. `"name"`, `"isrc"`); NULL = free-form |
| `proposed_value` | Text | yes | | suggested corrected value |
| `reason` | Text | yes | | reporter's free-text justification |
| `status` | Enum(ReportStatus) | no | `pending` | `pending \| approved \| rejected` |
| `reviewed_by` | Uuid FK→users.id | yes | | `ondelete=SET NULL`; admin who acted |
| `reviewed_at` | DateTime(tz) | yes | | |
| `review_note` | Text | yes | | admin note on the decision |
| `created_at`/`updated_at` | DateTime(tz) | no | now | |

Constraints/indexes: `INDEX (status)`; `INDEX (subject_type, subject_id)`; `INDEX (reporter_id)`.

> **No ALTER of any Plan 5 table (CONTRACT).** All six tables above are new. `votes` updates the pre-existing `upvotes/downvotes/net_score` counters on `matches`/`lyrics`/`entity_links` via `UPDATE` (data writes, not DDL). `matches.submitted_by` / `lyrics.submitted_by` are populated by submissions via `UPDATE`/insert — they already exist and stay FK-less (app-level integrity, per Plan 5's deferral rationale, so no SQLite batch-rebuild). Task 2's autogenerate-parity test proves migration `0002` adds exactly these six tables and touches no existing table.

---

## Token, password, vote, and rate-limit CONTRACTS (verbatim)

These blocks are the authoritative spec for Tasks 3, 8, and 11. Implementers copy them; the only freedom is internal.

### JWT access token (CONTRACT)
- **Type:** signed JWT (JWS), algorithm **HS256**, key = `settings.auth_secret_key` (`SecretStr`, required when `settings.auth_active()` — see Task 1; auth is inactive by default in `EMBEDDED` mode per spec §4).
- **Library:** PyJWT (`import jwt`).
- **Lifetime:** **15 minutes** (`settings.access_token_ttl_seconds`, default `900`).
- **Claims (exact):**
  ```json
  {
    "sub": "<user uuid as str>",
    "iat": <unix int>,
    "exp": <unix int>,
    "type": "access",
    "is_admin": <bool>
  }
  ```
  `is_admin` is embedded so the auth dependency needn't hit the DB per request; because the token lives ≤15 min, a demotion propagates within one refresh cycle. Admin routes additionally re-load the user (Task 10) so a disabled/demoted admin cannot act on a stale claim.
- **Verification:** `jwt.decode(token, key, algorithms=["HS256"], options={"require": ["exp","sub","type"]})`; `type` must equal `"access"`. Any `jwt.InvalidTokenError` (expired, bad signature, malformed) → treated as unauthenticated (no exception leaks to the client as 500).
- **No `jti`, no blacklist.** Revocation is via the refresh family + short TTL.

### Refresh token (CONTRACT — rotating, reuse-detecting)
- **Format:** opaque `secrets.token_urlsafe(32)` (~43 url-safe chars). **Not a JWT.** Never logged.
- **Storage:** `refresh_tokens.token_hash = sha256(token).hexdigest()`. Lookup is by hash.
- **Lifetime:** **30 days** (`settings.refresh_token_ttl_seconds`, default `2592000`). Each rotation issues a fresh 30-day token (sliding window). No absolute family cap in v1 (documented; a max-family-age cap is a future setting).
- **Delivery:** JSON response body, never a cookie (API-first; clients store it). Documented so web/CLI clients agree.
- **Rotation + reuse detection (state machine):**
  1. Client presents refresh token `R`. Compute `h = sha256(R)`. `SELECT ... WHERE token_hash = h` (row-lock on Postgres via `with_for_update`; SQLite serializes writes).
  2. **Not found** → `401 invalid_token`.
  3. **`revoked_at` is set** OR **`rotated_at` is set** (already spent) → **REUSE DETECTED**: revoke the *entire family* (`UPDATE refresh_tokens SET revoked_at = now WHERE family_id = R.family_id AND revoked_at IS NULL`) and return `401 invalid_token`. (A legitimate client never re-presents a spent token; a stolen-and-replayed token trips this.)
  4. **`expires_at <= now`** → `401 token_expired`; mark this row `revoked_at = now`.
  5. **Valid** → rotate: set `R.rotated_at = now`, mint new opaque `R'` with the **same `family_id`**, insert its row (`issued_at=now`, fresh `expires_at`), set `R.replaced_by = R'.id`. Mint a new access JWT. Return `{access_token, refresh_token: R'}`. All in one transaction.
- **Logout:** revoke the presented token's whole family (`revoked_at = now WHERE family_id = ...`). Access token expires on its own.

### Personal access token / PAT (CONTRACT)
- **Format:** `spdl_pat_` + `secrets.token_urlsafe(32)`. The literal prefix `spdl_pat_` is how the auth dependency distinguishes a PAT from a JWT.
- **Shown once:** full token returned only in the `POST` create response. Thereafter only `token_prefix` (`spdl_pat_` + first 6 secret chars) and metadata are listable.
- **Storage:** `api_tokens.token_hash = sha256(full_token).hexdigest()`; `token_prefix` stored for display.
- **Lifetime:** default none (`expires_at = NULL`); optional expiry via create request. Revocable (`revoked_at`).
- **Auth:** on `Bearer spdl_pat_...`, hash → lookup by `token_hash`; reject if `revoked_at` set or `expires_at <= now`; load `users` row; best-effort `UPDATE last_used_at = now`. Yields a `pat` `AuthContext`.

### Password hashing (CONTRACT — argon2id via argon2-cffi)
```python
from argon2 import PasswordHasher
from argon2.profiles import RFC_9106_LOW_MEMORY  # baseline; params pinned explicitly below

_HASHER = PasswordHasher(
    time_cost=3,          # iterations
    memory_cost=65536,    # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)  # argon2id is argon2-cffi's default type

def hash_password(password: str) -> str:        # returns encoded "$argon2id$v=19$m=65536,t=3,p=4$..."
def verify_password(encoded: str, password: str) -> bool:   # False on argon2.exceptions.VerifyMismatchError
def needs_rehash(encoded: str) -> bool:         # _HASHER.check_needs_rehash(encoded) — for param upgrades on login
```
- On successful **login**, if `needs_rehash(hash)` → recompute and persist (transparent upgrade).
- Password policy (register): min length 8, max 128 (bcrypt's 72-byte trap does not apply to argon2, but cap length to bound hashing cost). Enforced in the Pydantic request schema.

### Email normalization (CONTRACT)
```python
def normalize_email(email: str) -> str:
    """Trim, then casefold the whole address. Does NOT strip Gmail dots/plus-tags (v1)."""
    return email.strip().casefold()
```
Stored in `users.email`; the unique index is on this normalized value. Login normalizes the input before lookup. **No email verification in v1** — the spec (§6.1/§6.2) does not require it; accounts are usable immediately on register. Stated explicitly so no implementer adds a verification-token table.

### Vote state machine (CONTRACT — atomic tallies)
Endpoint body `{ "value": "up" | "down" | "retract" }`. `up`→`+1`, `down`→`-1`, `retract`→delete the vote. Let the existing vote for `(user, votable)` be `old ∈ {none, +1, -1}` and the request map to `new ∈ {+1, -1, retract}`. The counter deltas `(Δup, Δdown)` applied to the votable row are:

| old \ new | up (+1) | down (−1) | retract |
|---|---|---|---|
| **none** | (+1, 0) | (0, +1) | (0, 0) — no-op |
| **+1 (up)** | (0, 0) — no-op | (−1, +1) | (−1, 0) |
| **−1 (down)** | (+1, −1) | (0, 0) — no-op | (0, −1) |

Ledger action: `up`/`down` → INSERT (old=none) or UPDATE `votes.value` (old≠new); `retract` → DELETE the row (or no-op if none). `net_score` delta is always `Δup − Δdown`.

**Atomicity (never drift):** the whole operation runs in **one transaction**:
1. Lock/select the votable row (`SELECT ... FOR UPDATE` on Postgres via `with_for_update`; SQLite serializes writers, so correctness holds on both).
2. Read the caller's existing vote (unique `(user_id, votable_type, votable_id)`); the unique constraint makes concurrent double-insert impossible (one loses with `IntegrityError` → retried as an UPDATE).
3. Apply counters with **SQL expressions**, not read-modify-write in Python:
   `UPDATE matches SET upvotes = upvotes + :dup, downvotes = downvotes + :ddown, net_score = net_score + (:dup - :ddown) WHERE id = :id`.
4. Insert/update/delete the `votes` row.
5. Recompute the votable status (matches/entity_links) from the fresh tallies per the vote-policy config below.
6. Commit. Because counters mutate via expressions inside the locked transaction, tallies can never drift from the ledger; `net_score == upvotes - downvotes` is an invariant a test asserts by full re-tally.

### Vote policy — versioned config (CONTRACT — NOT magic numbers)
Modeled on the matcher's `ScoringConfig`/`matcher_version`: a frozen Pydantic model with a `policy_version` string, JSON round-trippable, so thresholds are recalibratable without code edits (spec §5 "versioned weights" philosophy).
```python
class VotePolicy(BaseModel):                 # frozen=True
    policy_version: str = "vote-v1"
    match_verify_net_score: int = 5          # matches.status -> community_verified when net_score >= this
    match_reject_net_score: int = -5         # matches.status -> rejected       when net_score <= this
    link_verify_net_score: int = 5           # entity_links.status -> verified
    link_dispute_net_score: int = -5         # entity_links.status -> disputed
    min_votes_for_status: int = 3            # require this many total votes (up+down) before any transition

VOTE_POLICY_V1 = VotePolicy()
```
- **Status is derived, recomputed after every vote** (no manual/admin match verification in v1):
  - `matches`: `community_verified` if `total_votes >= min_votes_for_status and net_score >= match_verify_net_score`; `rejected` if `total_votes >= min_votes_for_status and net_score <= match_reject_net_score`; else `auto`. (Transitions are reversible — a rejected match that recovers score returns to `auto` then `community_verified`. Community-submitted matches with `submitted_by != NULL` follow the same rule; there is no separate "pending" enum value — see submission contract.)
  - `entity_links`: same shape with `link_verify_net_score`/`link_dispute_net_score` → `verified`/`disputed`/`auto`.
  - `lyrics`: **no status column** (Plan 5 schema) — voting only maintains tallies; ordering by `net_score` (Plan 5 `LyricsRepository.list_for_track`) surfaces the community favorite.
- The active policy is injected (default `VOTE_POLICY_V1`); a hosted operator can pin a different `policy_version`. `matches.list_for_track` ordering (`community_verified` first) is unchanged — this plan only flips the `status` value.

### Rate-limit tiers (CONTRACT)
Enforced **only in hosted mode** (spec §6.4 "Rate limiting & abuse (hosted)"), or when `settings.rate_limit_enabled` is explicitly `True`. Gated at **startup** (middleware added or not), never per-request. Fixed-window counters keyed per tier.

| Tier | Applies to | Key | Limit | Window | Endpoints |
|---|---|---|---|---|---|
| `anon_read` | unauthenticated | client IP | 120 | 60 s | `GET` reads (resolve GET-equivalents, search, entity GETs, config) |
| `anon_auth` | unauthenticated | client IP | 20 | 60 s | `POST /auth/register`, `/auth/login`, `/auth/refresh`, OAuth callback (brute-force guard) |
| `authed_read` | user or PAT | token key | 600 | 60 s | `GET` reads |
| `authed_write` | user or PAT | token key | 60 | 60 s | votes, submissions, reports, PAT management, logout |

- **Anonymous catch-all (exact `classify` semantics):** the middleware runs before routing/dependencies, so an anonymous `POST /matches/{id}/vote` DOES pass through the limiter before `require_user` 401s it. Rule: **anonymous requests to non-auth paths — reads and writes alike — are classified `anon_read`** (keyed by IP); the mutating request then gets its cheap 401 from `require_user` downstream, so anonymous callers never consume an authed write budget and never reach tally logic. `anon_auth` covers only the listed public auth endpoints (credential-guessing throttle). There is deliberately no `anon_write` tier: an anonymous write is a guaranteed 401, so it is budgeted like any other anonymous request.
- **Key derivation** (no DB in the hot path): PAT → `"pat:" + sha256(secret)[:16]`; JWT → decode locally (signature only, no DB) → `"user:" + sub`; malformed/absent → `"ip:" + client_ip`.
- **Client IP (exact rule):** if `settings.client_ip_header` is set (e.g. `"cf-connecting-ip"`, `"x-forwarded-for"`) and the header is present, take the header value, **split on `","`, strip whitespace from each part, use index 0** (the original client in a proxy chain); if the header is unset, absent, or yields an empty string after stripping → fall back to `request.client.host`.
- **Operation class** by method+path prefix — full decision order: (1) authenticated + `GET` → `authed_read`; (2) authenticated + mutating method → `authed_write`; (3) anonymous + path in `AUTH_PATHS` → `anon_auth`; (4) anonymous otherwise (any method) → `anon_read`.
- **429 envelope** reuses Plan 5's contract: `ErrorEnvelope(code=ErrorCode.RATE_LIMITED, message="rate limit exceeded", detail={"limit": L, "window": W, "retry_after": S})` with a `Retry-After: S` header (seconds until window reset). Byte-identical shape to the provider `RateLimited` mapping.

```python
# spotdl_server/ratelimit/base.py  (CONTRACT — ONE interface, two backends)
@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int | None   # seconds; None when allowed

class RateLimiter(Protocol):
    async def hit(self, key: str, *, limit: int, window_s: int) -> RateLimitResult: ...
    async def aclose(self) -> None: ...
```
- `InMemoryRateLimiter(clock: Clock)` — default; per-key fixed-window counter dict, window boundary from `clock.now()`; the sole backend the test suite uses.
- `RedisRateLimiter(redis_client, clock)` — behind the optional `redis` extra; atomic `INCR` + `EXPIRE` (or a small Lua script) for a fixed window. **Constructed only when `settings.redis_url` is set AND the `redis` package is importable**; otherwise `InMemoryRateLimiter`. Selection happens once in the lifespan; the middleware sees only the `RateLimiter` interface.

### Auth dependency (CONTRACT — keeps Plan 5 routes anonymous)
```python
# spotdl_server/auth/context.py  (pure — no fastapi, no sqlalchemy)
@dataclass(frozen=True)
class AuthContext:
    kind: Literal["anonymous", "user", "pat"]
    user_id: UUID | None = None
    is_admin: bool = False
    token_id: UUID | None = None   # api_tokens.id when kind == "pat", else None
    @property
    def authenticated(self) -> bool: return self.kind != "anonymous"

ANONYMOUS = AuthContext(kind="anonymous")
```
```python
# spotdl_server/api/deps.py  (HTTP glue — may import fastapi + services + auth)
async def get_auth_context(request, session, clock) -> AuthContext:
    """Never raises for missing/invalid credentials — returns ANONYMOUS.
    - No Authorization header               -> ANONYMOUS
    - 'Bearer spdl_pat_...'                  -> validate PAT (DB) -> pat context or ANONYMOUS
    - 'Bearer <jwt>'                         -> verify JWT (no DB) -> user context or ANONYMOUS
    """

async def require_user(auth = Depends(get_auth_context)) -> AuthContext:
    """401 'authentication_required' if auth.kind == 'anonymous'."""

async def require_admin(auth = Depends(require_user), session = ...) -> AuthContext:
    """Re-load users row; 403 'forbidden' unless is_admin and is_active."""
```
- **Plan 5 routes stay anonymous-accessible:** they do **not** depend on `require_user`. `get_auth_context` is only added where a route wants to *know* the caller (optional) or where `require_user`/`require_admin` gate a write. No Plan 5 route signature changes; a regression test re-asserts every Plan 5 read route returns 200 with no `Authorization` header.

---

## Package layout produced by this plan

```
apps/server/src/spotdl_server/
├─ settings.py                     # extended: auth_secret_key, token TTLs, oauth creds, redis_url, rate-limit knobs (Task 1)
├─ db/
│  ├─ enums.py                     # + OAuthProvider, VotableType, ReportStatus (Task 1)
│  └─ models.py                    # + User, OAuthIdentity, RefreshToken, ApiToken, Vote, Report (Task 1)
├─ auth/                           # leaf utility package (pure; importable by services + api)
│  ├─ __init__.py
│  ├─ clock.py                     # Clock protocol, SystemClock (Task 3)          [CONTRACT]
│  ├─ passwords.py                 # argon2id hash/verify/needs_rehash (Task 3)    [CONTRACT]
│  ├─ tokens.py                    # JWT mint/verify, refresh/PAT mint+hash, TokenService (Task 3) [CONTRACT]
│  ├─ context.py                   # AuthContext, ANONYMOUS (Task 5)               [CONTRACT]
│  └─ oauth_providers.py           # OAuthProviderClient protocol + GitHub/Discord (Task 6) [CONTRACT]
├─ ratelimit/
│  ├─ __init__.py
│  ├─ base.py                      # RateLimiter protocol, RateLimitResult (Task 11) [CONTRACT]
│  ├─ memory.py                    # InMemoryRateLimiter (Task 11)
│  ├─ redis.py                     # RedisRateLimiter (Task 11, optional extra)
│  └─ tiers.py                     # tier table + key/op-class derivation (Task 11) [CONTRACT]
├─ policies/
│  └─ voting.py                    # VotePolicy, VOTE_POLICY_V1 (Task 8)           [CONTRACT]
├─ repositories/
│  ├─ users.py                     # UserRepository, OAuthIdentityRepository (Task 4) [CONTRACT]
│  ├─ tokens.py                    # RefreshTokenRepository, ApiTokenRepository (Task 4) [CONTRACT]
│  ├─ votes.py                     # VoteRepository (Task 8)                       [CONTRACT]
│  └─ reports.py                   # ReportRepository (Task 10)                    [CONTRACT]
├─ services/
│  ├─ auth.py                      # AuthService: register/login/logout/refresh/me (Task 5) [CONTRACT]
│  ├─ oauth.py                     # OAuthService: login-or-register + linking (Task 6) [CONTRACT]
│  ├─ pat.py                       # PatService: create/list/revoke (Task 7)       [CONTRACT]
│  ├─ voting.py                    # VoteService: state machine + status transitions (Task 8) [CONTRACT]
│  ├─ submissions.py               # SubmissionService: submit match URL (Task 9)  [CONTRACT]
│  ├─ reports.py                   # ReportService: submit + list own (Task 9/10)  [CONTRACT]
│  └─ admin.py                     # AdminService: users/reports/stats (Task 10)   [CONTRACT]
├─ api/
│  ├─ schemas.py                   # + auth/vote/submission/report/admin/config schemas (Tasks 5-12)
│  ├─ deps.py                      # + get_auth_context/require_user/require_admin, get_clock, service deps
│  └─ routers/
│     ├─ auth.py                   # /auth register|login|logout|refresh|me (Task 5)
│     ├─ oauth.py                  # /auth/oauth/{provider}/authorize|callback (Task 6)
│     ├─ tokens.py                 # /auth/tokens create|list|revoke (Task 7)
│     ├─ votes.py                  # /matches|lyrics|links/{id}/vote (Task 8)
│     ├─ submissions.py            # POST /tracks/{id}/matches (Task 9)
│     ├─ reports.py                # POST /reports, GET /reports/me (Task 9)
│     └─ admin.py                  # /admin users|reports|stats (Task 10)
alembic/versions/
└─ 0002_community_layer.py         # the six new tables (Task 2)                    [CONTRACT]

apps/server/tests/
├─ conftest.py                     # + FakeClock, user/token factory fixtures, in-memory limiter fixture
├─ db/            test_models_auth.py, test_migrations_0002.py
├─ auth/          test_passwords.py, test_tokens.py, test_oauth_providers.py
├─ repositories/  test_users_repo.py, test_tokens_repo.py, test_votes_repo.py, test_reports_repo.py
├─ services/      test_auth_service.py, test_oauth_service.py, test_pat_service.py,
│                 test_vote_service.py, test_submission_service.py, test_report_service.py, test_admin_service.py
├─ ratelimit/     test_memory_limiter.py, test_tiers.py
└─ api/           test_auth_api.py, test_oauth_api.py, test_pat_api.py, test_vote_api.py,
                  test_submission_api.py, test_report_api.py, test_admin_api.py,
                  test_ratelimit_middleware.py, test_config_community.py, test_anonymous_read_unaffected.py
```

---

## Tasks

### Task 1: New settings, DB enums, and the six ORM models

**Files:**
- Modify: `apps/server/pyproject.toml` (deps), `src/spotdl_server/settings.py`, `db/enums.py`, `db/models.py`
- Create: `apps/server/tests/db/test_models_auth.py`

**Step 1 — dependencies.** Add to `apps/server/pyproject.toml` `dependencies` (floors verified on PyPI 2026-07): `"pyjwt>=2.10"`, `"argon2-cffi>=23.1"`, `"httpx>=0.28"`. Add an **optional extra**:
```toml
[project.optional-dependencies]
redis = ["redis>=5.2"]
```
`respx` and `httpx` are already in the root dev group. Run `uv sync --all-packages`.

**Step 2 — extend `Settings` (RED via `test_models_auth.py` only needs enums/models; settings tested in Task 3/11, but add the fields now to avoid churn).** Add:
```python
auth_enabled: bool | None = None               # None -> derive from mode (spec §4: EMBEDDED has no auth)
auth_secret_key: SecretStr | None = None       # required (validated) when auth is active and mode is HOSTED
access_token_ttl_seconds: int = 900            # 15 min
refresh_token_ttl_seconds: int = 2_592_000     # 30 days
voting_enabled: bool = True                    # effective only when auth is active
# OAuth (provider enabled iff both id+secret present)
github_client_id: str | None = None
github_client_secret: SecretStr | None = None
discord_client_id: str | None = None
discord_client_secret: SecretStr | None = None
oauth_redirect_base_url: str | None = None      # e.g. https://api.spotdl.example ; callback = {base}/api/v1/auth/oauth/{provider}/callback
web_auth_redirect_enabled: bool | None = None   # None -> True (the server serves the SPA in every mode); browser handoff on the OAuth callback (Task 6)
spa_base_url: str | None = None                 # SPA origin for the OAuth browser handoff; None -> same origin (relative 302)
# Rate limiting
rate_limit_enabled: bool | None = None          # None -> derive: True iff mode is HOSTED
redis_url: str | None = None
client_ip_header: str | None = None             # e.g. "cf-connecting-ip"
```
Add helpers (methods, not fields):
- `def auth_active(self) -> bool` — **the embedded-mode gate (spec §4: embedded = "none (loopback only)")**: `self.auth_enabled if self.auth_enabled is not None else self.mode is not DeploymentMode.EMBEDDED`. Analogous to `rate_limit_active()`. In `EMBEDDED` mode the auth/oauth/tokens/votes/submissions/reports/admin routers are **not mounted** unless the operator explicitly sets `SPOTDL_AUTH_ENABLED=true`; setting `false` disables them in any mode.
- `def rate_limit_active(self) -> bool` (`self.rate_limit_enabled if not None else self.mode is DeploymentMode.HOSTED`).
- `def enabled_oauth_providers(self) -> list[OAuthProvider]` (those with id+secret set).
- `def require_auth_secret(self) -> str` (raise `RuntimeError` if `auth_active()` and key missing — called at startup, Task 5/12).

> **Community-router mount rule (CONTRACT, used by Tasks 5-10):** every router this plan adds (auth, oauth, tokens, votes, submissions, reports, admin) is mounted in `create_app` **only when `settings.auth_active()`** (oauth additionally requires `enabled_oauth_providers()` non-empty). Startup-time gating, mirroring Plan 5's download-router seam — never per-request conditionals.

**Step 3 — `db/enums.py`.** Append `OAuthProvider`, `VotableType`, `ReportStatus` exactly as in the CONTRACT.

**Step 4 — write `test_models_auth.py` (RED).** Mirrors Plan 5's `test_models.py` mechanically:
- `test_new_tables_present` — `Base.metadata.tables` now additionally contains `{users, oauth_identities, refresh_tokens, api_tokens, votes, reports}` (and still all eleven Plan-5 tables — no removals).
- One `test_<table>_columns` per new table: full column list, nullability, defaults from the contract, asserted against a literal expected dict.
- `test_users_email_unique` — insert two users with same `email` → `IntegrityError`; `uq_users_email` present by name.
- `test_oauth_identity_unique_constraints` — `uq_oauth_identities_provider_provider_account_id` and `uq_oauth_identities_user_id_provider` present; duplicate provider account → `IntegrityError`.
- `test_refresh_token_hash_unique` and `test_api_token_hash_unique`.
- `test_votes_unique_and_check` — `uq_votes_user_id_votable_type_votable_id` present; `CHECK value IN (-1,1)` (`ck_votes_value_in_range`) rejects `value=0` / `value=2`.
- `test_new_enum_columns_non_native_varchar` — `OAuthProvider`/`VotableType`/`ReportStatus`/`EntityType`(reports.subject_type) columns have `native_enum is False`; round-trip insert-read `OAuthProvider.GITHUB`, `VotableType.MATCH`, `ReportStatus.PENDING`.
- `test_fk_ondelete_rules` — `oauth_identities.user_id`/`refresh_tokens.user_id`/`api_tokens.user_id`/`votes.user_id` are CASCADE; `reports.reporter_id`/`reports.reviewed_by` are SET NULL; deleting a user cascades their oauth/refresh/pat/votes rows and NULLs their reports.
- `test_votes_have_no_votable_fk` and `test_reports_have_no_subject_fk` — `votes.votable_id` and `reports.subject_id` carry **no** ForeignKey (polymorphic-by-design guard).
- `test_no_plan5_table_altered` — assert `matches`/`lyrics`/`entity_links` column sets are byte-identical to Plan 5 (import the expected dicts from Plan 5's test module or re-declare) — proves additive-only.

**Step 5 — implement in `db/models.py`.** Add one `class` per table inheriting `Base` (+ `TimestampMixin`), encoding every column/type/default/constraint/index per the contract. `Vote.value` uses a `CheckConstraint("value IN (-1, 1)", name="value_in_range")` in `__table_args__`. Relationships (optional, `lazy="selectin"`): `User.oauth_identities`, `User.api_tokens`. Do **not** add relationships from `matches`/`lyrics`/`entity_links` to `votes` (polymorphic — no relationship).

**Gates:** `make check` green (mypy strict). **Commit:** `feat(server): community-layer ORM models (users/oauth/tokens/votes/reports)`.

---

### Task 2: Alembic migration `0002` — the six tables, dual-dialect + parity

**Files:**
- Create: `apps/server/alembic/versions/0002_community_layer.py`
- Create: `apps/server/tests/db/test_migrations_0002.py`

**Step 1 — write `test_migrations_0002.py` (RED).** Parallels Plan 5's `test_migrations.py`, reusing its `postgres` marker/fixture:
- SQLite (always): fresh tmp DB, `alembic upgrade head` (runs `0001` then `0002`); assert reflected tables == `Base.metadata.tables` keys (all seventeen). `alembic downgrade -1` (to `0001`); assert the six new tables are gone and the eleven Plan-5 tables remain intact. `alembic downgrade base`; assert only `alembic_version` remains.
- **Parity:** after `upgrade head` on fresh SQLite, `alembic.autogenerate.compare_metadata` returns `[]` (migration == models across both `0001` + `0002`) — the anti-churn guarantee.
- **Additive proof:** after `downgrade -1` (at `0001`), assert `matches`/`lyrics`/`entity_links` reflected columns are unchanged — `0002` created no ALTER on them.
- Postgres (gated by `SPOTDL_TEST_POSTGRES_URL`): same up/down + parity.

**Step 2 — implement `0002_community_layer.py`.** `down_revision = "0001"`. Generate via `alembic revision --autogenerate -m "community layer"`, then hand-verify it renders exactly the six tables with the naming convention, non-native enum VARCHAR+CHECK, the vote CHECK, and every unique/index from the contract — and **no** `alter_table` / `add_column` on any Plan-5 table (delete any spurious diff). `downgrade()` drops the six tables in FK-safe order (`votes`, `reports`, `api_tokens`, `refresh_tokens`, `oauth_identities`, `users`).

**Gates:** `make check` green (SQLite path). **Commit:** `feat(server): alembic 0002 community-layer migration (six new tables)`.

---

### Task 3: Auth crypto leaf — Clock, argon2id passwords, token service

**Files:**
- Create: `auth/__init__.py`, `auth/clock.py`, `auth/passwords.py`, `auth/tokens.py`
- Create: `tests/auth/__init__.py`, `tests/auth/test_passwords.py`, `tests/auth/test_tokens.py`
- Modify: `tests/conftest.py` (add `FakeClock`)

**Contract vs freedom:** `Clock`, the password functions, and `TokenService`'s public API are **CONTRACT** (services + the auth dependency depend on them). These modules import **no** FastAPI and **no** SQLAlchemy (pure), so they sit below `services`.

**`auth/clock.py` (CONTRACT):**
```python
class Clock(Protocol):
    def now(self) -> datetime: ...       # tz-aware UTC
class SystemClock:
    def now(self) -> datetime: return datetime.now(UTC)
```
`FakeClock` (in `conftest.py`): holds a mutable `datetime`, `advance(seconds)` — the single time-control seam for token expiry, rotation, PAT expiry, and rate-limit windows.

**`auth/passwords.py` (CONTRACT):** exactly the argon2id block above — `hash_password`, `verify_password`, `needs_rehash`, module `_HASHER` with the pinned params.

**`auth/tokens.py` (CONTRACT):**
```python
def sha256_hex(token: str) -> str: ...
def new_refresh_token() -> str:  # secrets.token_urlsafe(32)
def new_pat() -> tuple[str, str]:  # (full "spdl_pat_...", token_prefix)  -- prefix = "spdl_pat_" + first 6 secret chars
def is_pat(token: str) -> bool:  # token.startswith("spdl_pat_")

@dataclass(frozen=True)
class AccessClaims:
    user_id: UUID; is_admin: bool

class TokenService:
    def __init__(self, *, secret: str, clock: Clock,
                 access_ttl_s: int = 900, refresh_ttl_s: int = 2_592_000) -> None: ...
    def mint_access(self, *, user_id: UUID, is_admin: bool) -> str: ...       # HS256 JWT per claims contract
    def verify_access(self, token: str) -> AccessClaims | None: ...           # None on any InvalidTokenError / wrong type
    def refresh_expiry(self) -> datetime: ...                                 # clock.now() + refresh_ttl
```
`mint_access` sets `iat`/`exp` from `clock.now()` so `FakeClock` fully controls expiry.

**Tests (offline):**
- `test_passwords.py`: `test_hash_and_verify_roundtrip`; `test_verify_rejects_wrong_password`; `test_hash_is_argon2id` (encoded starts `"$argon2id$"`); `test_needs_rehash_false_for_current_params`; `test_needs_rehash_true_after_param_change` (hash with a weaker `PasswordHasher`, assert `needs_rehash` True); `test_hashes_are_salted` (two hashes of same password differ).
- `test_tokens.py`: `test_mint_and_verify_access` (round-trip user_id+is_admin); `test_verify_expired_returns_none` (mint, `clock.advance(901)`, verify → None); `test_verify_tampered_signature_returns_none`; `test_verify_wrong_type_returns_none` (hand-craft a JWT with `type="refresh"`); `test_verify_bad_secret_returns_none`; `test_new_pat_prefix_and_shape` (`is_pat` True, prefix matches, full != prefix); `test_sha256_hex_stable`.

**Gates:** `make check` green. **Commit:** `feat(server): argon2id passwords + JWT/refresh/PAT token service`.

---

### Task 4: Auth repositories — users, oauth identities, refresh & api tokens

**Files:**
- Create: `repositories/users.py`, `repositories/tokens.py`
- Create: `tests/repositories/test_users_repo.py`, `tests/repositories/test_tokens_repo.py`

**Contract vs freedom:** class names + public signatures are CONTRACT. All take `AsyncSession` in `__init__`, take/return ORM models or plain values, never Pydantic/HTTP types. Repositories never commit.

**`UserRepository` (CONTRACT):**
```python
class UserRepository:
    def __init__(self, session): ...
    async def get(self, user_id: UUID) -> User | None: ...
    async def get_by_email(self, normalized_email: str) -> User | None: ...
    async def create(self, *, email: str, password_hash: str | None,
                     display_name: str | None = None, is_admin: bool = False) -> User: ...
    async def set_password_hash(self, user: User, password_hash: str) -> None: ...   # rehash upgrade
    async def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]: ...  # (page, total) for admin
```

**`OAuthIdentityRepository` (CONTRACT):**
```python
class OAuthIdentityRepository:
    def __init__(self, session): ...
    async def get_by_provider_account(self, provider: OAuthProvider, account_id: str) -> OAuthIdentity | None: ...
    async def link(self, *, user_id: UUID, provider: OAuthProvider,
                   provider_account_id: str, provider_username: str | None) -> OAuthIdentity: ...
```

**`RefreshTokenRepository` (CONTRACT):**
```python
class RefreshTokenRepository:
    def __init__(self, session): ...
    async def create(self, *, user_id, token_hash, family_id, expires_at) -> RefreshToken: ...
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...   # with_for_update on Postgres
    async def mark_rotated(self, token: RefreshToken, *, replaced_by: UUID, now: datetime) -> None: ...
    async def revoke_family(self, family_id: UUID, *, now: datetime) -> int: ...   # returns rows revoked
    async def revoke(self, token: RefreshToken, *, now: datetime) -> None: ...
```

**`ApiTokenRepository` (CONTRACT):**
```python
class ApiTokenRepository:
    def __init__(self, session): ...
    async def create(self, *, user_id, name, token_prefix, token_hash, expires_at) -> ApiToken: ...
    async def get_by_hash(self, token_hash: str) -> ApiToken | None: ...
    async def list_for_user(self, user_id: UUID) -> list[ApiToken]: ...
    async def touch_last_used(self, token: ApiToken, *, now: datetime) -> None: ...  # best-effort
    async def revoke(self, token: ApiToken, *, now: datetime) -> None: ...
    async def get_owned(self, token_id: UUID, user_id: UUID) -> ApiToken | None: ...
```

**Tests (offline, in-memory SQLite, reuse Plan 5's `session` fixture):** create+get user; `get_by_email` normalization is the caller's job (store normalized, look up normalized); duplicate email → `IntegrityError`; oauth link + `get_by_provider_account`; refresh create/get-by-hash/`mark_rotated`/`revoke_family` (count matches family size, already-revoked skipped); api token create with prefix+hash, `list_for_user` excludes nothing but marks revoked, `get_owned` returns None for another user's token id (ownership guard); `touch_last_used` updates timestamp.

**Gates:** `make check` green. **Commit:** `feat(server): user/oauth/refresh/api-token repositories`.

---

### Task 5: AuthContext + auth dependency + AuthService + `/auth` router

**Files:**
- Create: `auth/context.py`, `services/auth.py`
- Create: `api/routers/auth.py`; modify `api/deps.py`, `api/schemas.py`, `app.py` (lifespan builds `Clock` + `TokenService` factory; mount router when `auth_active()`)
- Create: `tests/services/test_auth_service.py`, `tests/api/test_auth_api.py`, `tests/api/test_anonymous_read_unaffected.py`

**Contract vs freedom:** `AuthContext`, `get_auth_context`/`require_user`/`require_admin`, and `AuthService`'s public API are CONTRACT.

**`auth/context.py`** — exactly the CONTRACT block (`AuthContext`, `ANONYMOUS`).

**`api/deps.py` additions:**
- `get_clock(request) -> Clock` (reads `request.app.state.clock`).
- `get_token_service(request, clock) -> TokenService` (built from settings secret + TTLs; secret via `settings.require_auth_secret()`).
- `get_auth_context(request, session, token_service) -> AuthContext` — exactly the CONTRACT behavior: PAT branch (hash→`ApiTokenRepository.get_by_hash`, reject revoked/expired, load user, `touch_last_used`, `pat` context); JWT branch (`token_service.verify_access` → `user` context, `is_admin` from claim); else `ANONYMOUS`. **Never raises.**
- `require_user` → 401 `ErrorCode.AUTH_REQUIRED`; `require_admin` → re-load user, 403 `ErrorCode.FORBIDDEN` unless `is_admin and is_active`.
- `get_auth_service(session, token_service, clock)`.

**New `ErrorCode` values (extend `api/errors.py` + `_status_and_code` — the complete Plan 6 set, declared once here):**

| `ErrorCode` member | value | HTTP | Backing exception (`services/errors.py`, subclass `SpotdlError`) | Raised by |
|---|---|---|---|---|
| `AUTH_REQUIRED` | `authentication_required` | 401 | `AuthRequired` | `require_user` (Task 5) |
| `INVALID_CREDENTIALS` | `invalid_credentials` | 401 | `InvalidCredentials` | login (Task 5) |
| `INVALID_TOKEN` | `invalid_token` | 401 | `InvalidToken` | refresh reuse/not-found, bad OAuth state (Tasks 5/6) |
| `TOKEN_EXPIRED` | `token_expired` | 401 | `TokenExpired` | expired refresh (Task 5) |
| `FORBIDDEN` | `forbidden` | 403 | `Forbidden` | `require_admin` (Tasks 5/10) |
| `EMAIL_TAKEN` | `email_taken` | 409 | `EmailTaken` | register duplicate (Task 5) |
| `OAUTH_EMAIL_REQUIRED` | `oauth_email_required` | 400 | `OAuthEmailRequired` | OAuth provider returned no email (Task 6) |
| `NOT_AN_AUDIO_TARGET` | `not_an_audio_target` | 400 | `NotAnAudioTarget` | match submission with a non-audio/non-track URL (Task 9) |

All eight enum members and exception classes are added in **this task** (single home, one `_status_and_code` extension); Tasks 6 and 9 raise `OAuthEmailRequired`/`NotAnAudioTarget` from services. Same treatment as Plan 5's `NotFoundError`: exception carries the message, handler maps to the envelope. (No `ALREADY_EXISTS` code — every conflict this plan raises is the specific `EMAIL_TAKEN`; a generic code with no raise site would be dead vocabulary.) The auth router may also raise `HTTPException` directly for pure-HTTP cases, but domain errors go through the envelope. Task 5 tests include `test_new_error_codes_mapped` — unit-test `_status_and_code` for each row above, constructing each exception as defined.

**`AuthService` (CONTRACT):**
```python
class AuthService:
    def __init__(self, *, session, token_service: TokenService, clock: Clock,
                 users: UserRepository, refresh_tokens: RefreshTokenRepository) -> None: ...
    async def register(self, *, email, password, display_name=None) -> TokenPair: ...
    async def login(self, *, email, password) -> TokenPair: ...
    async def refresh(self, *, refresh_token: str) -> TokenPair: ...
    async def logout(self, *, refresh_token: str) -> None: ...      # revoke family; idempotent
    async def get_me(self, user_id: UUID) -> User: ...
```
`TokenPair` = dataclass `{access_token, refresh_token, user}`. Algorithms:
- **register:** `normalize_email`; `hash_password`; `users.create` (raise `EmailTaken` on `IntegrityError`); mint access + create a new refresh family (`family_id = uuid4`), commit; return pair. **No email verification** (documented).
- **login:** normalize; `get_by_email`; if missing OR `verify_password` fails → `InvalidCredentials` (generic; no user enumeration); if `needs_rehash` → `set_password_hash`; if `not is_active` → `InvalidCredentials`; issue new refresh family + access.
- **refresh:** the reuse-detection state machine (CONTRACT): hash→`get_by_hash`; not found→`InvalidToken`; revoked/rotated→`revoke_family` + `InvalidToken`; expired→`revoke` + `TokenExpired`; else `mark_rotated(replaced_by=new.id)` + create successor in same family + mint access.
- **logout:** hash→`get_by_hash`; if found → `revoke_family`; always succeed (idempotent).

**`api/routers/auth.py`** (prefix `/api/v1/auth`, ≤200 lines, no ORM): `POST /register` (`RegisterRequest{email: EmailStr, password: constr(min_length=8,max_length=128), display_name?}`), `POST /login`, `POST /refresh` (`{refresh_token}`), `POST /logout` (`{refresh_token}`, requires user), `GET /me` (requires user or PAT) → `UserResponse{id, email, display_name, is_admin, created_at}`. `TokenResponse{access_token, refresh_token, token_type="bearer", expires_in, user}`.

**Lifespan (`app.py`):** build `app.state.clock = SystemClock()`; `create_app` calls `settings.require_auth_secret()` at startup when `auth_active()` (fail fast on missing secret in hosted). Mount the auth router only when `settings.auth_active()` (the community-router mount rule, Task 1) — in `EMBEDDED` mode (default `auth_enabled=None`) no auth routes exist.

**Tests (offline; `FakeClock`; in-memory DB):**
- service: register→login round-trip; duplicate register → `EmailTaken`; login wrong password / unknown email → `InvalidCredentials` (identical message); inactive user login → `InvalidCredentials`; refresh rotates (old token now rotated, new works); **reuse detection**: refresh with an already-rotated token → whole family revoked, subsequent valid successor also 401; expired refresh (`clock.advance(refresh_ttl+1)`) → `TokenExpired`; logout revokes family (refresh after logout → 401); `needs_rehash` path upgrades stored hash on login.
- api: `POST /register` → 201 with tokens; `GET /me` with returned access token → 200; `GET /me` with no header → 401 `authentication_required`; `GET /me` with PAT (row seeded) → 200; expired access token → 401 `token_expired`/`invalid_token`; refresh endpoint round-trip.
- `test_anonymous_read_unaffected.py`: every Plan 5 read route (`GET /health`, `/config`, `/search`, `/tracks/{id}`, `/tracks/{id}/matches`, `/tracks/{id}/lyrics`, `POST /resolve`) returns its Plan-5 status with **no** `Authorization` header — proves auth wiring did not gate reads.

**Gates:** `make check` green. **Commit:** `feat(server): email+password auth (register/login/logout/rotating refresh) + auth dependency`.

---

### Task 6: OAuth — GitHub + Discord authorization-code flow (offline-tested)

**Files:**
- Create: `auth/oauth_providers.py`, `services/oauth.py`, `api/routers/oauth.py`
- Modify: `api/deps.py`, `api/schemas.py`, `app.py` (mount when any provider configured)
- Create: `tests/auth/test_oauth_providers.py`, `tests/services/test_oauth_service.py`, `tests/api/test_oauth_api.py`

**Contract vs freedom:** the `OAuthProviderClient` protocol + the DTOs it returns are CONTRACT; concrete GitHub/Discord internals are free.

**`auth/oauth_providers.py` (CONTRACT — pure httpx, no fastapi/DB):**
```python
@dataclass(frozen=True)
class OAuthUserInfo:
    provider_account_id: str
    email: str | None
    username: str | None

class OAuthProviderClient(Protocol):
    provider: OAuthProvider
    def authorize_url(self, *, state: str, redirect_uri: str) -> str: ...
    async def exchange_code(self, *, code: str, redirect_uri: str) -> str: ...      # returns provider access token
    async def fetch_user_info(self, *, access_token: str) -> OAuthUserInfo: ...

class GitHubOAuth(OAuthProviderClient): ...   # authorize github.com/login/oauth/authorize; token; api.github.com/user (+ /user/emails)
class DiscordOAuth(OAuthProviderClient): ...   # discord.com/api/oauth2/authorize|token; /users/@me
def build_oauth_client(provider, *, client_id, client_secret, http: httpx.AsyncClient) -> OAuthProviderClient: ...
```
Each concrete client takes an injected `httpx.AsyncClient` (so respx intercepts it) and its credentials. Scopes: GitHub `read:user user:email`; Discord `identify email`.

**State (CSRF) — stateless HMAC (CONTRACT):** `state = base64url(nonce || exp) + "." + hmac_sha256(auth_secret, payload)`; `sign_state(clock, ttl=600)` / `verify_state(state, clock)` in `services/oauth.py`. No DB row for state.

**`OAuthService` (CONTRACT):**
```python
class OAuthService:
    def __init__(self, *, session, token_service, clock,
                 users: UserRepository, identities: OAuthIdentityRepository,
                 refresh_tokens: RefreshTokenRepository,
                 clients: dict[OAuthProvider, OAuthProviderClient]) -> None: ...
    def authorize_url(self, provider: OAuthProvider) -> str: ...     # signs state, returns provider URL
    async def complete(self, provider: OAuthProvider, *, code: str, state: str) -> TokenPair: ...
```
`complete` (login-or-register + linking):
1. `verify_state` (raise `InvalidToken` on bad/expired state).
2. `exchange_code` → provider token; `fetch_user_info`.
3. If `identities.get_by_provider_account(provider, info.provider_account_id)` → existing user.
4. Elif `info.email` and `users.get_by_email(normalize_email(info.email))` → **link** identity to that user.
5. Else **require an email**: if `info.email` is None, raise `OAuthEmailRequired` (Task 5's `ErrorCode.OAUTH_EMAIL_REQUIRED`, 400) — no synthesized placeholder emails. (GitHub/Discord `email` scope is requested, so this is the rare private-email case.) Otherwise create the user (`password_hash=None`, email = normalized provider email) then `identities.link`.
6. Mint our access + new refresh family. Return `TokenPair`.

**`api/routers/oauth.py`** (prefix `/api/v1/auth/oauth`, ≤200 lines): `GET /{provider}/authorize` → 307 redirect to `authorize_url` (or JSON `{authorize_url}` when `?json=true`, for clients that open their own browser); `GET /{provider}/callback?code=&state=` → completes per the **callback response contract** below. Unknown/disabled provider → 404. `redirect_uri` computed from `settings.oauth_redirect_base_url` + fixed path.

**OAuth callback response (CONTRACT — dual-mode; browser handoff is an additive mode, JSON semantics unchanged).** The provider redirects the user's **browser** to the callback as a top-level navigation, so a raw JSON body there would strand the SPA (Plan 10's finding). Mode selection, evaluated per request in this order:
1. **JSON mode** — when `settings.web_auth_redirect_enabled` resolves `False`, **or** the request prefers JSON (`Accept` header contains `application/json` at a q-value ≥ any `text/html` entry; the CLI, generated clients, and existing tests send `Accept: application/json`): return the documented `TokenResponse` (200) or `ErrorEnvelope` exactly as already specified. **No existing contract row changes semantics for JSON consumers.**
2. **Browser-handoff mode** — otherwise (the default for a plain browser navigation; `web_auth_redirect_enabled=None` resolves `True` since the server serves the SPA in every mode): respond **302** with `Location = {spa_base}/auth/callback/{provider}` where `spa_base = settings.spa_base_url or ""` (None → same-origin relative redirect), carrying the token pair in the **URL fragment — never the query string** (fragments are not transmitted to servers, so tokens never appear in server/proxy logs or `Referer` headers). Fragment format and parameter names pinned exactly:
   `#access_token=<jwt>&refresh_token=<opaque>&token_type=bearer&expires_in=<access ttl seconds>`
   The SPA route `/auth/callback/{provider}` (Plan 10) parses the fragment, stores the pair, and immediately replaces the history entry to clear it.
3. **Errors in browser-handoff mode:** state verification failure → **302** to `{spa_base}/auth/callback/{provider}` with fragment `#error=oauth_state_mismatch` (pinned value; no envelope body — the SPA renders the failure). Other domain failures use the same mechanism with the envelope code as the value (e.g. `#error=oauth_email_required`). In JSON mode these stay the existing 401 `invalid_token` / 400 `oauth_email_required` envelopes.

**`build_oauth_clients(settings, http)`** dependency assembles the `clients` dict from `settings.enabled_oauth_providers()`. `app.state.http` = a shared `httpx.AsyncClient` built in the lifespan (closed on shutdown). Mount the oauth router only when `settings.auth_active()` **and** `enabled_oauth_providers()` is non-empty.

**Tests — fully offline (respx + a `FakeOAuthProvider`):**
- `test_oauth_providers.py`: with `respx` mocking `github.com`/`api.github.com` and `discord.com`, assert `authorize_url` shape (client_id, scope, redirect_uri, state), `exchange_code` posts code and returns token, `fetch_user_info` parses `OAuthUserInfo` (GitHub two-call email path; Discord single call). **No real network** (respx asserts all routes mocked).
- `test_oauth_service.py`: with a `FakeOAuthProvider` implementing the protocol (canned `OAuthUserInfo`): new account → user+identity created, tokens issued; second login same provider account → same user (no dup); provider email matching an existing password user → identity **linked** to that user; bad state → `InvalidToken`; provider returns no email → `OAuthEmailRequired` (api layer: 400 `oauth_email_required` envelope).
- `test_oauth_api.py`: `GET /authorize?json=true` returns an `authorize_url` containing a signed `state`; feed that state back to `GET /callback` (service wired with a fake client) with `Accept: application/json` → `TokenResponse` (JSON mode); tampered state + `Accept: application/json` → 401 `invalid_token`; disabled provider → 404. **Browser-handoff mode:** callback with a browser-like `Accept: text/html,...` → 302, `Location` starts with `/auth/callback/github` (same-origin default), tokens in the **fragment** with the pinned names `access_token`/`refresh_token`/`token_type=bearer`/`expires_in` and the **query string carries no token**; with `spa_base_url="https://app.example"` → `Location` starts with `https://app.example/auth/callback/github`; tampered state in handoff mode → 302 with fragment `#error=oauth_state_mismatch` (no token params); `web_auth_redirect_enabled=False` → browser-like request still gets JSON `TokenResponse` (mode toggle honored).

**Gates:** `make check` green. **Commit:** `feat(server): GitHub/Discord OAuth login-or-register (offline-tested)`.

---

### Task 7: PATs — create / list / revoke for the CLI

**Files:**
- Create: `services/pat.py`, `api/routers/tokens.py`
- Modify: `api/deps.py`, `api/schemas.py`, `app.py`
- Create: `tests/services/test_pat_service.py`, `tests/api/test_pat_api.py`

**`PatService` (CONTRACT):**
```python
class PatService:
    def __init__(self, *, session, clock, api_tokens: ApiTokenRepository) -> None: ...
    async def create(self, *, user_id, name, expires_at: datetime | None = None) -> tuple[ApiToken, str]: ...  # (row, full_token shown ONCE)
    async def list_for_user(self, user_id) -> list[ApiToken]: ...
    async def revoke(self, *, user_id, token_id) -> None: ...   # ownership-checked; 404 if not owned
```
`create` uses `new_pat()` (Task 3) → stores `token_prefix` + `sha256_hex(full)`; returns the full token exactly once.

**`api/routers/tokens.py`** (prefix `/api/v1/auth/tokens`, all `require_user`, ≤200 lines): `POST /` (`CreatePatRequest{name, expires_in_days?: int}`) → `PatCreatedResponse{id, name, token_prefix, token, created_at, expires_at}` (**`token` present only here**); `GET /` → `list[PatResponse{id, name, token_prefix, last_used_at, expires_at, revoked_at, created_at}]` (never the token); `DELETE /{token_id}` → 204 (revoke; 404 if not owned via `get_owned`).

**PAT acceptance in the dependency is already wired in Task 5** (`get_auth_context` PAT branch). This task adds a test that a PAT minted here authenticates `GET /auth/me`.

**Tests (offline):** service create returns full token once; hash stored, prefix stored; `list_for_user` never exposes hash/full; revoke sets `revoked_at`; revoking another user's token id → not-found (ownership); api: create → use the returned PAT as `Authorization: Bearer spdl_pat_...` on `GET /auth/me` → 200 (`pat` context); revoked PAT → 401; expired PAT (`FakeClock.advance`) → 401.

**Gates:** `make check` green. **Commit:** `feat(server): personal access tokens (create/list/revoke) for CLI auth`.

---

### Task 8: Voting — policy config, state machine, atomic tallies, status transitions

**Files:**
- Create: `policies/__init__.py`, `policies/voting.py`, `repositories/votes.py`, `services/voting.py`, `api/routers/votes.py`
- Modify: `api/deps.py`, `api/schemas.py`, `app.py`
- Create: `tests/services/test_vote_service.py`, `tests/repositories/test_votes_repo.py`, `tests/api/test_vote_api.py`

**Contract vs freedom:** `VotePolicy`/`VOTE_POLICY_V1`, `VoteService.vote` semantics, and the atomic tally rule are CONTRACT.

**`policies/voting.py`** — exactly the `VotePolicy` CONTRACT block, JSON round-trippable (`model_dump_json`/`model_validate_json`), frozen.

**`VoteRepository` (CONTRACT):**
```python
class VoteRepository:
    def __init__(self, session): ...
    async def get_vote(self, *, user_id, votable_type: VotableType, votable_id: UUID) -> Vote | None: ...
    async def upsert_value(self, *, user_id, votable_type, votable_id, value: int) -> Vote: ...
    async def delete(self, vote: Vote) -> None: ...
    async def apply_tally_delta(self, votable_type, votable_id, *, d_up: int, d_down: int) -> None: ...
        # UPDATE <table> SET upvotes = upvotes + :d_up, downvotes = downvotes + :d_down,
        #                    net_score = net_score + (:d_up - :d_down) WHERE id = :id
    async def load_tallies(self, votable_type, votable_id) -> tuple[int, int, int] | None: ...  # (up, down, net) or None if votable missing
    async def set_match_status(self, match_id, status: MatchStatus) -> None: ...
    async def set_link_status(self, link_id, status: LinkStatus) -> None: ...
```
`apply_tally_delta` dispatches to the right table by `votable_type` (match→matches, lyrics→lyrics, entity_link→entity_links). The `UPDATE ... SET col = col + :delta` form is the atomicity guarantee — no Python read-modify-write.

**`VoteService` (CONTRACT):**
```python
class VoteService:
    def __init__(self, *, session, votes: VoteRepository, policy: VotePolicy = VOTE_POLICY_V1) -> None: ...
    async def vote(self, *, user_id: UUID, votable_type: VotableType, votable_id: UUID,
                   action: Literal["up", "down", "retract"]) -> VoteOutcome: ...
```
Algorithm (one transaction): verify the votable exists (`load_tallies` → `NotFoundError` if None); read existing vote; compute `(Δup, Δdown)` from the state-machine table; `apply_tally_delta`; insert/update/delete the ledger row (unique constraint = race guard, retry-as-update on `IntegrityError`); reload tallies; recompute status per policy (`set_match_status`/`set_link_status`; lyrics: none); commit. `VoteOutcome` = dataclass `{votable_type, votable_id, upvotes, downvotes, net_score, status: str | None, your_vote: int | None}`.

**`api/routers/votes.py`** (≤200 lines, all `require_user`): `POST /api/v1/matches/{id}/vote`, `POST /api/v1/lyrics/{id}/vote`, `POST /api/v1/links/{id}/vote`, each body `VoteRequest{value: Literal["up","down","retract"]}` → `VoteResponse` (mirrors `VoteOutcome`). Each router fn maps the path to a `VotableType` and delegates. Unknown/absent votable id → 404 `not_found`.

**Tests (offline):**
- repo: `apply_tally_delta` on each table type moves the right counters and `net_score`; `load_tallies` None for missing id.
- service state machine — table-driven over all 9 `(old, new)` transitions asserting `(Δup, Δdown)` and final tallies; `test_double_up_is_noop`; `test_change_up_to_down`; `test_retract_removes_row_and_decrements`; `test_retract_with_no_vote_is_noop`.
- **atomicity/invariant:** `test_net_score_equals_up_minus_down_after_random_sequence` — apply a randomized sequence of votes from several users, then assert `net_score == upvotes - downvotes` and that summing the ledger rows reproduces the counters (no drift).
- **status transitions:** with `min_votes_for_status=3`, drive a match from `auto`→`community_verified` at `net_score>=5`, back to `auto`, then to `rejected` at `net_score<=-5`; same for entity_links `verified`/`disputed`; lyrics never gets a status (only tallies + ordering).
- **policy is config:** `test_custom_policy_changes_threshold` — inject a `VotePolicy(match_verify_net_score=2)`, verify verification at a lower score; `test_policy_json_roundtrip`.
- api: `POST /matches/{id}/vote {value:"up"}` unauthenticated → 401; authenticated → 200 with updated tallies + `your_vote=1`; unknown match id → 404; lyrics/links parallel.

**Gates:** `make check` green. **Commit:** `feat(server): community voting with atomic tallies and versioned status policy`.

---

### Task 9: Submissions — submit match URL; metadata-correction reports

**Files:**
- Create: `services/submissions.py`, `services/reports.py`, `repositories/reports.py`, `api/routers/submissions.py`, `api/routers/reports.py`
- Modify: `api/deps.py`, `api/schemas.py`, `app.py`
- Create: `tests/services/test_submission_service.py`, `tests/services/test_report_service.py`, `tests/repositories/test_reports_repo.py`, `tests/api/test_submission_api.py`, `tests/api/test_report_api.py`

**Match submission (§6.2 `POST /tracks/{id}/matches`).**

**`SubmissionService` (CONTRACT):**
```python
COMMUNITY_MATCHER_VERSION = "community"     # sentinel stored in matches.matcher_version for user submissions

class SubmissionService:
    def __init__(self, *, session, tracks: TrackRepository, matches: MatchRepository) -> None: ...
    async def submit_match(self, *, track_id: UUID, url: str, submitted_by: UUID) -> MatchModel: ...
```
Algorithm:
1. `tracks.get(track_id)` → `NotFoundError` if absent.
2. `ref = parse(url)` (core) → `UnsupportedURL` (→ 400) on unparseable input.
3. Validate `ref.provider` is an **audio** provider (`YTMUSIC | YOUTUBE | SOUNDCLOUD | BANDCAMP | PIPED`) and `ref.entity_type == EntityType.TRACK`; otherwise raise `NotAnAudioTarget` (Task 5's `ErrorCode.NOT_AN_AUDIO_TARGET`, 400) — Spotify/Deezer/iTunes/MusicBrainz URLs are metadata-only, not playable targets.
4. Upsert a `matches` row by the Plan 5 unique `(track_id, target_provider, target_id)`:
   - `target_provider=ref.provider`, `target_id=ref.entity_id`, `target_url=ref.url or url`,
   - `score=0.0`, `matcher_version=COMMUNITY_MATCHER_VERSION`, `status=MatchStatus.AUTO`, `submitted_by=submitted_by`,
   - denormalized `candidate_*` left NULL (no synchronous provider fetch in v1 — documented; a later enrichment job can backfill).
   - **If the row already exists:** return it unchanged (idempotent); if it was algorithmic (`submitted_by IS NULL`) leave it as-is (do not overwrite provenance). This reuses Plan 5's `MatchRepository` (extend it with a narrow `create_submission`/`get_by_target` helper if `replace_for_track` is too coarse — additive, no schema change).
3'. **No separate "pending" status:** the schema `MatchStatus` has only `auto|community_verified|rejected`. A community submission is `status=auto` **with `submitted_by != NULL`** (algorithmic matches have `submitted_by IS NULL`). It becomes `community_verified` purely through Task 8 voting. This is exactly the provenance Plan 5 reserved `submitted_by` for — no schema change, no ALTER.

**`api/routers/submissions.py`** (`require_user`, ≤200 lines): `POST /api/v1/tracks/{id}/matches` body `SubmitMatchRequest{url: str}` → 201 `MatchOut` (the Plan 5 schema). Reuses `require_user` so anonymous → 401.

> **Lyrics submission is NOT in §6.2 (explicit scope note).** §6.2 lists `GET /tracks/{id}/lyrics` and `POST /lyrics/{id}/vote` only — there is **no** lyrics-submission endpoint in the spec (the "submit URL" pattern is defined for matches alone). v1 therefore does **not** add `POST /tracks/{id}/lyrics`; community involvement with lyrics is limited to voting on provider-sourced lyrics (Task 8). The symmetric submission path is a clean future extension (`LyricsRepository.upsert(..., submitted_by=...)` already fits) and is left out deliberately, not by omission.

**Metadata-correction reports (§6.2 `POST /reports`).**

**`ReportRepository` (CONTRACT):**
```python
class ReportRepository:
    def __init__(self, session): ...
    async def create(self, *, reporter_id, subject_type: EntityType, subject_id: UUID,
                     field: str | None, proposed_value: str | None, reason: str | None) -> Report: ...
    async def get(self, report_id) -> Report | None: ...
    async def list_by_reporter(self, reporter_id) -> list[Report]: ...
    async def list_by_status(self, status: ReportStatus, *, limit, offset) -> tuple[list[Report], int]: ...
    async def set_decision(self, report: Report, *, status: ReportStatus,
                           reviewed_by: UUID, note: str | None, now: datetime) -> None: ...
```

**`ReportService` (CONTRACT):**
```python
class ReportService:
    def __init__(self, *, session, clock, reports: ReportRepository) -> None: ...
    async def submit(self, *, reporter_id, subject_type, subject_id, field, proposed_value, reason) -> Report: ...
    async def list_own(self, reporter_id) -> list[Report]: ...
```
`submit` validates `subject_type` is a real `EntityType` and creates a `pending` report. (Existence of the subject entity is **not** hard-verified in v1 — reports may target entities the reporter saw; admin triage judges validity. Documented.)

**`api/routers/reports.py`** (`require_user`, ≤200 lines): `POST /api/v1/reports` body `CreateReportRequest{subject_type: EntityType, subject_id: UUID, field?: str, proposed_value?: str, reason?: str}` → 201 `ReportResponse{id, subject_type, subject_id, field, proposed_value, reason, status, created_at}`; `GET /api/v1/reports/me` → `list[ReportResponse]` (own reports). (Scope note: `GET /reports/me` is not in §6.2's literal endpoint list — it is a deliberate minimal addition so a reporter can see the review state of their own submissions; drop it if the reviewer prefers strict spec parity.)

**Tests (offline):**
- submission service: valid YouTube URL on existing track → match row `status=auto`, `submitted_by` set, `matcher_version="community"`; unknown track → `NotFoundError`; Spotify URL → `NotAnAudioTarget` (api layer: 400 `not_an_audio_target` envelope); garbage → `UnsupportedURL` (400); duplicate submit → idempotent (one row); submitting a target that already exists as an algorithmic match → returns it without clobbering `submitted_by`.
- submission api: `POST /tracks/{id}/matches` unauth → 401; auth → 201 `MatchOut`; then `GET /tracks/{id}/matches` (Plan 5) includes it.
- report service/repo: submit creates pending; `list_own`; `list_by_status`/`set_decision` (used by admin) transitions and stamps `reviewed_by/at/note`.
- report api: `POST /reports` unauth → 401; auth → 201; `GET /reports/me` returns own.

**Gates:** `make check` green. **Commit:** `feat(server): community match submissions + metadata-correction reports`.

---

### Task 10: Minimal admin — users, reports queue, stats

**Files:**
- Create: `services/admin.py`, `api/routers/admin.py`
- Modify: `api/deps.py`, `api/schemas.py`, `app.py`
- Create: `tests/services/test_admin_service.py`, `tests/api/test_admin_api.py`

**`AdminService` (CONTRACT):**
```python
class AdminService:
    def __init__(self, *, session, clock,
                 users: UserRepository, reports: ReportRepository) -> None: ...
    async def list_users(self, *, limit, offset) -> tuple[list[User], int]: ...
    async def reports_queue(self, *, status: ReportStatus = PENDING, limit, offset) -> tuple[list[Report], int]: ...
    async def decide_report(self, *, report_id, reviewer_id, approve: bool, note: str | None) -> Report: ...
    async def stats(self) -> AdminStats: ...
```
`decide_report`: load report (`NotFoundError` if absent); `set_decision(status=APPROVED|REJECTED, reviewed_by=reviewer_id, note, now)`. **v1 does not auto-apply** an approved correction to canonical data — the decision records the review state only (spec §1 non-goal: "Full moderation suite"; §6.2 "Admin (minimal)"). Documented so no implementer wires an entity mutation here.
`AdminStats` = dataclass `{users_total, matches_total, community_verified_matches, rejected_matches, votes_total, reports_pending, reports_total}` computed via `SELECT count(*)` aggregates (a small `StatsRepository` or inline count queries — repository layer).

**`api/routers/admin.py`** (prefix `/api/v1/admin`, **all `require_admin`**, ≤200 lines):
- `GET /users?limit=&offset=` → `PagedUsers{items: list[AdminUserResponse], total}`.
- `GET /reports?status=pending&limit=&offset=` → `PagedReports{items: list[ReportResponse], total}`.
- `POST /reports/{id}/approve` and `POST /reports/{id}/reject` (body `{note?: str}`) → `ReportResponse`. (Two explicit verbs beat a mutable PATCH for a minimal audited queue.)
- `GET /stats` → `AdminStatsResponse`.

**Tests (offline):** seed an admin user + a normal user; `require_admin` blocks non-admin (403 `forbidden`) and anonymous (401); admin lists users (pagination `total`); reports queue filters by status; approve/reject stamps `reviewed_by/at/status/note` and is reflected in the queue; `GET /stats` returns correct counts after seeding votes/matches/reports; a demoted admin (claim says admin but `is_admin` now False in DB) is rejected by `require_admin` (re-load guard).

**Gates:** `make check` green. **Commit:** `feat(server): minimal admin (users, reports queue, stats)`.

---

### Task 11: Rate limiting — interface, in-memory + Redis backends, tiers, middleware

**Files:**
- Create: `ratelimit/__init__.py`, `ratelimit/base.py`, `ratelimit/memory.py`, `ratelimit/redis.py`, `ratelimit/tiers.py`, `api/middleware.py` (or `api/ratelimit_middleware.py`)
- Modify: `app.py` (lifespan builds limiter; add middleware when active), `api/errors.py` (429 body helper), `settings.py`
- Create: `tests/ratelimit/__init__.py`, `tests/ratelimit/test_memory_limiter.py`, `tests/ratelimit/test_tiers.py`, `tests/api/test_ratelimit_middleware.py`

**Contract vs freedom:** the `RateLimiter` protocol + `RateLimitResult`, the tier table, and the 429 envelope are CONTRACT.

**`ratelimit/base.py`** — exactly the `RateLimiter`/`RateLimitResult` CONTRACT block.

**`ratelimit/memory.py`** — `InMemoryRateLimiter(clock: Clock)`: dict `key -> (window_start, count)`; on `hit`, if `clock.now()` past `window_start + window_s` reset; increment; `allowed = count <= limit`; `retry_after = ceil(window_end - now)` when blocked. `aclose()` no-op. Deterministic under `FakeClock`.

**`ratelimit/redis.py`** — `RedisRateLimiter(client, clock)`: `INCR key` then `EXPIRE key window_s NX` (or one Lua script for atomicity); `retry_after` from `PTTL`. Imported lazily; the module top guards `import redis.asyncio`. Not exercised by the default suite (documented; a `network`/`redis`-marked test may cover it in CI).

**`ratelimit/tiers.py` (CONTRACT):**
```python
class Tier(StrEnum): ANON_READ; ANON_AUTH; AUTHED_READ; AUTHED_WRITE
TIERS: dict[Tier, tuple[int, int]] = {   # (limit, window_s)
    Tier.ANON_READ: (120, 60), Tier.ANON_AUTH: (20, 60),
    Tier.AUTHED_READ: (600, 60), Tier.AUTHED_WRITE: (60, 60),
}
AUTH_PATHS: frozenset[str]    # {"/api/v1/auth/register","/api/v1/auth/login","/api/v1/auth/refresh", "<oauth callback prefix>"}
def classify(request, *, authenticated: bool) -> tuple[Tier, str]:
    """Return (tier, key). key = 'pat:'|'user:'|'ip:' prefixed per the CONTRACT (no DB)."""
def client_ip(request, header: str | None) -> str: ...
```
Key derivation reads the `Authorization` header and decodes the JWT **locally** (via a `TokenService.verify_access` passed in, or a signature-only decode) — no DB; PAT → hash prefix; else IP.

**Middleware** (`api/middleware.py`) — a Starlette `BaseHTTPMiddleware` (or pure ASGI): resolve `(tier, key)` via `classify`; `result = await limiter.hit(key, limit, window_s)`; if `not result.allowed` → return `JSONResponse(429, ErrorEnvelope(code=RATE_LIMITED, message=..., detail={"limit","window","retry_after"}).model_dump(), headers={"Retry-After": str(retry_after)})`; else call `next` and optionally set `X-RateLimit-Remaining`. The middleware reads `request.app.state.rate_limiter` and the local token verifier.

**Wiring (startup gating, no per-request mode `if`):** in `create_app`, `if settings.rate_limit_active(): app.add_middleware(RateLimitMiddleware, ...)`. Lifespan builds `app.state.rate_limiter`: `RedisRateLimiter` iff `settings.redis_url` set and `redis` importable, else `InMemoryRateLimiter(app.state.clock)`; `await rate_limiter.aclose()` on shutdown. When not active, no middleware is added — Plan 5's and this plan's routes behave exactly as if rate limiting did not exist.

**Tests (offline, `FakeClock`, in-memory backend):**
- `test_memory_limiter.py`: under limit → allowed with decreasing `remaining`; at limit+1 → blocked with `retry_after`; `clock.advance(window_s)` resets; two keys are independent.
- `test_tiers.py`: `classify` returns `ANON_READ` for anon GET, `ANON_READ` for an anonymous POST to a non-auth path (the catch-all — it will 401 downstream), `ANON_AUTH` for login/register/refresh, `AUTHED_WRITE` for a PAT POST vote, `AUTHED_READ` for a user GET; `client_ip` honors `client_ip_header` including multi-value `X-Forwarded-For` (`"1.2.3.4, 10.0.0.1"` → `"1.2.3.4"`) and falls back to `request.client.host` when unset/absent/empty.
- `test_ratelimit_middleware.py`: build an app with `rate_limit_enabled=True` and an injected `FakeClock` + in-memory limiter; hammer `GET /config` past `anon_read` from one IP → 429 with `Retry-After` and the `rate_limited` envelope; a different IP unaffected; `clock.advance(60)` → allowed again; authenticated caller (seeded PAT/JWT) gets the higher `authed_read` budget; login endpoint throttled at `anon_auth` (20/min). Assert an app with `rate_limit_active()` False (selfhost default) never 429s regardless of volume (middleware not mounted).

**Gates:** `make check` green. **Commit:** `feat(server): tiered rate limiting (in-memory default, optional redis) with hosted-only enforcement`.

---

### Task 12: `/config` extension, OpenAPI regeneration, layering contracts, integration smoke

**Files:**
- Modify: `api/schemas.py` (`FeatureFlags`, `ConfigResponse`), `api/routers/meta.py`, `scripts/export_openapi.py` (mode note), `openapi.json` (regenerated), `.importlinter`, `Makefile` (no change if `openapi` target exists)
- Modify: `tests/api/test_config.py` (Plan 5) → extend; create `tests/api/test_config_community.py`, `tests/test_openapi.py` (extend), `tests/test_layering.py` (extend), `tests/api/test_integration_community_flow.py`

**Step 1 — `/config` extension (spec §4).** Flip the Plan 5 hardcoded flags to computed and add OAuth providers:
- `FeatureFlags.auth = settings.auth_active()` (was hardcoded `False`) — **`False` by default in `EMBEDDED` mode** (spec §4: embedded auth = "none (loopback only)").
- `FeatureFlags.voting = settings.voting_enabled and settings.auth_active()` (voting needs accounts; also `False` in embedded by default).
- `ConfigResponse` gains `oauth_providers: list[str]` = `[p.value for p in settings.enabled_oauth_providers()] if settings.auth_active() else []` (empty when auth inactive or none configured). `downloads`/`library`/`matcher_version` unchanged.
Values are startup-fixed (settings don't change at runtime). Extend `test_config.py` / `test_config_community.py`:
- hosted/selfhost defaults: `auth=true`, `voting=true`; embedded default: `auth=false`, `voting=false`, `oauth_providers=[]`.
- explicit override: `Settings(mode=EMBEDDED, auth_enabled=True, auth_secret_key=...)` → `auth=true` (opt-in honored).
- `oauth_providers` reflects configured creds (test sets `github_client_id`/secret → `["github"]`).
- **`test_embedded_mounts_no_community_routes`** — build the app with `Settings(mode=DeploymentMode.EMBEDDED)` (defaults) and assert **no route path** under `/api/v1/auth*`, `/api/v1/admin*`, `/api/v1/reports*`, and no `*/vote` or `POST /tracks/{id}/matches` route exists (iterate `app.routes`); the Plan 5 read surface is still fully mounted. This is the embedded-gating regression guard, the sibling of Plan 5's `test_no_download_routes_mounted_in_any_mode`.

**Step 2 — OpenAPI regeneration + in-sync (extends Plan 5's `make openapi`).** All new routers are mounted in the fixed export mode. Because auth/voting/oauth routers mount only when enabled, `scripts/export_openapi.py` must build the app with a **fully-enabled** settings profile (`Settings(mode=SELFHOST, auth_enabled=True, voting_enabled=True, github_client_id="x", github_client_secret="x", discord_client_id="x", discord_client_secret="x", auth_secret_key="test")`) so every community route appears in the committed `openapi.json`. Document this in the script. Run `make openapi`; commit the regenerated `openapi.json`. `tests/test_openapi.py`: the in-sync test still passes (regenerate → byte-compare); add `test_community_routes_documented` asserting `/auth/login`, `/matches/{id}/vote`, `/tracks/{id}/matches`, `/reports`, `/admin/stats`, `/auth/tokens` are present in the schema paths, and that the new `ErrorCode` values appear.

**Step 3 — layering contracts (`.importlinter` + `test_layering.py`).** Extend Plan 5's contracts:
- Add `auth` and `ratelimit` and `policies` as leaf utility packages: they must **not** import `fastapi`, `services`, `repositories`, or `sqlalchemy` — add a `forbidden` contract `source_modules = spotdl_server.auth | spotdl_server.ratelimit | spotdl_server.policies`, `forbidden_modules = fastapi | spotdl_server.services | spotdl_server.repositories`. (`ratelimit.redis` importing `redis` is fine; `auth.oauth_providers` importing `httpx` is fine.)
- The existing `routers_no_orm` and `services_no_fastapi` contracts now also cover the new routers/services — verify `api/routers/{auth,oauth,tokens,votes,submissions,reports,admin}.py` import no `sqlalchemy`/ORM, and `services/{auth,oauth,pat,voting,submissions,reports,admin}.py` import no `fastapi`. `api/middleware.py` is HTTP glue (may import fastapi + ratelimit + services helpers) — place it at the `api.routers` layer level like `deps.py`.
- `test_layering.py`: extend the AST scan to the new router/service files; re-assert every file in `api/routers/` is ≤200 lines (the new routers included).

**Step 4 — integration smoke (`test_integration_community_flow.py`, offline end-to-end).** Real in-memory DB migrated via **Alembic `upgrade head`** (proves `0002` is the real schema), fake provider registry (Plan 5 fakes) so a track exists, `httpx.ASGITransport`, `FakeClock`, `auth_enabled=True`:
1. `POST /auth/register` → tokens; `GET /auth/me` → 200.
2. `POST /resolve {spotify track url}` (Plan 5 path) → a canonical track id.
3. `POST /tracks/{id}/matches {youtube url}` (Bearer access) → 201 community match (`submitted_by` set, `status=auto`).
4. Two more registered users `POST /matches/{match_id}/vote {up}` → after crossing `min_votes_for_status` + `match_verify_net_score`, `GET /tracks/{id}/matches` shows `status=community_verified` first.
5. One user retracts → status recomputed; tallies still satisfy `net == up - down`.
6. `POST /reports {metadata_correction}` → pending; an admin user (`is_admin=True` seeded) `POST /admin/reports/{id}/approve` → status approved; `GET /admin/stats` reflects counts.
7. `POST /auth/refresh` rotates; replay the old refresh token → 401 (family revoked). `POST /auth/logout` → subsequent refresh 401.
This is the Plan 6 acceptance test.

**Step 5 — verify `uv run lint-imports` passes** with the new contracts.

**Gates:** `make check` green. **Commit:** `test(server): config/openapi/layering + offline community integration flow`.

---

## Self-review

**Every §6.2 auth/community endpoint is routed.** `POST /resolve`/`GET /search`/entity GETs/matches/lyrics stay as Plan 5. New here: `auth/register|login|logout|refresh|me` (Task 5), OAuth `authorize|callback` for GitHub+Discord (Task 6), PAT `create|list|revoke` (Task 7), `POST /matches/{id}/vote` + `/lyrics/{id}/vote` + `/links/{id}/vote` (Task 8), `POST /tracks/{id}/matches` (Task 9), `POST /reports` + `GET /reports/me` (Task 9), admin `users`/`reports` queue + approve/reject + `stats` (Task 10). Explicitly out of scope and **not** added: a lyrics-submission endpoint (not in §6.2 — stated in Task 9), `GET /metrics` (Prometheus, Plan 11), downloads/WS (Plan 7).

**No ALTER of any Plan 5 table.** Verified against `plan-5-draft.md`: `matches`/`lyrics`/`entity_links` already carry `upvotes/downvotes/net_score` (used by `VoteRepository.apply_tally_delta` via `UPDATE`), and `submitted_by`/`requested_by` are FK-less nullable UUIDs (populated by submissions). Migration `0002` adds exactly six new tables; `votes.user_id`/`reports.reporter_id` FK into the new `users` table (additive); `votes.votable_id`/`reports.subject_id` are polymorphic (no cross-table FK, matching Plan 5's `entity_links.entity_id` precedent). Task 1 `test_no_plan5_table_altered` and Task 2 additive-proof + autogenerate-parity mechanically enforce this.

**Tokens are specified precisely enough to implement without judgment calls.** JWT access = HS256, exact claim set, 15-min TTL, `type="access"` required, invalid→unauthenticated (never 500). Refresh = opaque `token_urlsafe(32)`, stored `sha256` hex, 30-day sliding, family-based rotation with the full reuse-detection state machine (found/revoked-or-rotated/expired/valid branches enumerated). PAT = `spdl_pat_` prefix, `token_urlsafe(32)`, hashed storage, prefix for display, shown once, optional expiry, revocable; prefix is the JWT-vs-PAT discriminator. Passwords = argon2id with pinned `time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16` and login-time rehash. Email normalized (`strip().casefold()`); **no email verification in v1** (stated). All time flows through an injectable `Clock`.

**Vote tallies never drift (atomicity stated).** The 9-cell `(old,new)→(Δup,Δdown)` transition table is fixed; counters mutate via SQL `col = col + :delta` expressions inside one locked transaction (`with_for_update` on Postgres; serialized writes on SQLite); the unique `(user_id, votable_type, votable_id)` constraint is the concurrent-double-insert guard; `net_score` is recomputed as `net_score + (Δup − Δdown)`; a randomized-sequence test re-tallies the ledger and asserts `net_score == upvotes − downvotes`. Status transitions are derived from tallies via the **versioned `VotePolicy`** (`policy_version="vote-v1"`, JSON round-trippable, injectable) — thresholds are config, not magic numbers, mirroring the matcher's `ScoringConfig`.

**Rate limiting matches the spec.** Four tiers (anon read/auth, authed read/write) with explicit limits/windows; the anonymous catch-all is exact — anonymous non-auth requests (reads **and** writes) are budgeted under `anon_read` by IP, and anonymous writes are then 401'd by `require_user` before any tally logic, so they never consume an authed write budget; `client_ip` has an exact multi-value parse rule (split on comma, strip, index 0); enforcement is **hosted-only** (`rate_limit_active()` derives from mode unless overridden) and gated at **startup** (middleware mounted or not — no per-request mode `if`); 429 reuses Plan 5's `ErrorEnvelope`/`ErrorCode.RATE_LIMITED` with `Retry-After`; ONE `RateLimiter` interface with an in-memory default (the only backend the suite uses, driven by `FakeClock`) and an optional Redis backend selected only when `redis_url` is set and the `redis` extra is installed.

**Auth dependency keeps Plan 5 anonymous.** `get_auth_context` returns `ANONYMOUS` for missing/invalid credentials and never raises; Plan 5 read routes do not depend on it (`test_anonymous_read_unaffected` re-asserts every read route works header-less). `require_user`/`require_admin` gate only the new writes; `require_admin` re-loads the user so a stale admin claim cannot act.

**Embedded mode has no auth surface (spec §4).** `auth_active()` derives from mode exactly like `rate_limit_active()`: `EMBEDDED` → community routers (auth, oauth, tokens, votes, submissions, reports, admin) are **not mounted** and `/config` reports `auth=false`, `voting=false`, `oauth_providers=[]`, unless the operator explicitly opts in with `SPOTDL_AUTH_ENABLED=true`. Gating is a mount-time decision (the community-router mount rule, Task 1), enforced by `test_embedded_mounts_no_community_routes` (Task 12) — the sibling of Plan 5's no-download-routes guard.

**Error-code vocabulary is closed and fully wired.** All eight new codes are declared once in Task 5 with a status/exception/raise-site table (`authentication_required`, `invalid_credentials`, `invalid_token`, `token_expired`, `forbidden`, `email_taken`, `oauth_email_required`, `not_an_audio_target`); every code has a backing exception in `services/errors.py` and a real raise site (Tasks 5/6/9/10); no dead codes (a generic `already_exists` was deliberately dropped — nothing raises it), and `test_new_error_codes_mapped` unit-tests each `_status_and_code` row.

**Consistency with Plan 5 contracts.** Same cross-dialect type rules (UUID PK, non-native enum VARCHAR+CHECK, `TimestampMixin`, naming convention, portable JSON), same layering (routers ≤200 lines / no ORM; services / no FastAPI; repositories = sole ORM), same error envelope extended with new codes through the existing table-driven `_status_and_code`, same OpenAPI in-sync mechanism extended for community routes, same offline-first testing with the provider-registry fakes and now `FakeClock` + in-memory limiter + respx for OAuth. Simpler than the reference branch (no token blacklist; opaque rotating refresh; argon2id; PyJWT).

**Dependency choices justified.** **PyJWT over python-jose:** python-jose (the reference branch's `jose`) is effectively unmaintained and pulls JWE/JWK machinery v5 never uses; PyJWT is actively maintained, smaller, and covers HS256 JWS exactly. **argon2-cffi** for argon2id (memory-hard, modern default) over bcrypt. **redis** is an optional extra, never a default dependency. Floors: `pyjwt>=2.10`, `argon2-cffi>=23.1`, `httpx>=0.28`, `redis>=5.2` (extra); dev `respx>=0.22` already present.

**OAuth callback works for both browsers and machine clients (Plan 10 cross-check).** The callback is dual-mode by CONTRACT: browser top-level navigations get a 302 to the SPA route `/auth/callback/{provider}` with the pinned fragment `#access_token=…&refresh_token=…&token_type=bearer&expires_in=…` (fragment, never query — tokens stay out of server logs and `Referer`), state failures redirect with `#error=oauth_state_mismatch`; JSON consumers (CLI/tests sending `Accept: application/json`, or `web_auth_redirect_enabled=False`) keep the original `TokenResponse`/`ErrorEnvelope` semantics unchanged — the handoff mode is purely additive. Both modes are tested in `test_oauth_api.py`.

**No TBDs.** Every task lists exact files, signatures, and test names. The one bounded implementer choice (`MatchRepository` gains a narrow submission helper vs reusing `replace_for_track`) is stated with the v1 decision made, not left open; the former OAuth-callback JSON-vs-redirect choice is now resolved by the dual-mode callback contract (Task 6).
