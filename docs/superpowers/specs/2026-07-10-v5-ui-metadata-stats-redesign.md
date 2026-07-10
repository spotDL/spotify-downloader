# spotDL v5 — UI Redesign + Multi-Provider Metadata + Stats

**Status:** approved direction (Emerald-forward + full maximalism, both surfaces).
**Supersedes:** the ad-hoc TUI redesign contract at `.superpowers/sdd/tui-redesign-contract.md`
(kept for reference; this document is now the binding design).

## Goal

Rebuild both the web UI and the terminal UI on one cohesive "Midnight Vinyl /
Emerald" design system; make search universal (artists · albums · tracks ·
playlists); make every canonical entity carry metadata merged from **all**
providers (Spotify first for display) with the per-provider breakdown visible;
and add a songstats-style engagement **Stats** panel from the metrics providers
actually expose.

## Global Constraints

- **One palette, two renderers.** Web (Tailwind v4 CSS vars in `apps/web/src/index.css`)
  and TUI (`apps/cli/.../tui/app.tcss` + `theme.py`) use the SAME token values.
- **Accent:** primary `#00d084` (emerald), focus `#00d084`, secondary `#4ecdc4`
  (teal), warn/gold `#ffd93d`, error `#ff3333`. Backgrounds (dark, layered):
  void `#08080a`, chassis `#0f1012`, panel `#161819`, elevated `#1c1e20`,
  surface `#242628`, hover `#2c2e32`. Text: `#fafafa` / `#a8a8b3` / `#6b6b76` /
  `#454550`. Borders `#2f2f33` / subtle `#232326`. Dark-only (both surfaces).
- **Polish = full maximalism:** blurred cover-art hero backdrops, film-grain
  overlay, glassmorphism panels, circular VU score gauges (green ≥90 / gold
  70–89 / red <70), beat-pulse BPM, shimmer skeletons, staggered entrance,
  hover-lift. All motion gated by `prefers-reduced-motion` / a reduce-motion
  setting.
- **Fonts (web):** Satoshi (display), General Sans (body), JetBrains Mono (all
  numeric/technical data). Self-hosted (bundled), never CDN-linked. TUI keeps
  terminal fonts; mono-for-data is the DataTable/StatChip convention.
- **Score scale stays 0–100** on the wire (matcher v4 parity); clients normalize
  for gauges. **Match.score is 0–100** — do not change.
- **Spotify is the display source of truth.** `SOURCE_PRIORITY = Spotify >
  Deezer > iTunes > MusicBrainz` governs which provider wins each canonical
  field. Unchanged.
- Existing quality gates stay green: `make check`, golden matching corpus
  (never regress from 0.9813), Playwright e2e, import-linter, generated-client
  in-sync tests. Every DTO change regenerates BOTH clients (Python + TS).

## Phase 1 — Foundation (design tokens + data model)

### 1a. Design tokens
- Replace `apps/web/src/index.css` `@theme` with the palette above; add the
  maximalism utility layer (`.grain`, `.glass`, `.hero-backdrop`, `.vu-gauge`,
  `.beat`, `.shimmer`, hover-lift), font `@font-face` data-URI blocks, and the
  type scale (`.text-display/headline/title`, mono-data).
- Rewrite `app.tcss` `$` tokens + mirror them in `theme.py Theme` so widget
  `DEFAULT_CSS` (which can't read `$vars`) uses the same hex.

### 1b. Data model (Alembic migration, SQLite + Postgres)
New canonical fields (all nullable, Spotify-first merged):
- **Artist:** `popularity int`, `followers int`, `bio text`, `country str`,
  `header_url str` (for the hero backdrop, distinct from `image_url` avatar).
- **Album:** `label str`, `copyright_text str`, `popularity int`, `genres JSON`,
  `album_type str` (album/single/ep/compilation — re-added as a soft label only,
  NOT an entity type; drives the discography filter + badge).
- **Track:** already has `popularity`, `date`, `publisher`, `copyright_text` on
  the core model — ensure they persist to the canonical row (`publisher`,
  `copyright_text`, `date`, `key`/`bpm`/audio-features JSON if a provider gives
  them; audio features are best-effort, absent for most providers).
- **New table `entity_stat`** (time-series engagement): `id`, `entity_type`,
  `entity_id`, `provider`, `metric` (followers|fans|views|listeners|playcount|
  popularity|rank), `value bigint`, `captured_at`. One row per (entity, provider,
  metric, capture). Powers the Stats panel + sparklines.
- **Metadata-sources view:** expose the existing `provider_snapshots` for an
  entity as a typed `MetadataSourceView` (provider, fetched_at, the fields it
  contributed) so the UI's "Metadata Sources" panel can render per-provider data.

## Phase 2 — Universal search

- Extend the provider layer with typed search. Add protocol
  `SearchesEntities` (optional capability) with
  `async def search_entities(query, *, types: set[EntityType], limit) ->
  list[SearchHit]` where `SearchHit` is a lightweight preview union
  (entity_type + name + provider ref + cover + subtitle + optional stat).
  - Spotify: one call `GET /v1/search?type=track,album,artist,playlist`.
  - Deezer: parallel `/search/track|album|artist|playlist`.
  - iTunes/MusicBrainz/YTMusic: implement what they support; others fall back to
    track-only via the existing `Searches`.
- `provider_search` gains a typed variant that fans out, merges per type, dedups.
- `SearchResult` DTO grows: `tracks`, `albums`, `artists`, `playlists` (each a
  tuple of preview views) + `degraded_sources`. Snapshot track + album + artist
  hits so resolve-on-open is a cache hit.
- UI: sectioned, color-coded results (per-type divider + count), a filter tab bar
  (All / Songs / Artists / Albums / Playlists), list/grid toggle for albums, and
  a ⌘K / Ctrl+K command-palette variant. Web + TUI.

## Phase 3 — Cross-provider metadata enrichment

- On resolve (track/album/artist/playlist), after the primary provider fetch,
  fan out a bounded lookup to the OTHER providers and merge their snapshots:
  - **Track:** match by ISRC (fallback name+artist) across providers.
  - **Artist / Album:** match by normalized name (+ album_artist / year for
    albums). Best-effort; a miss is non-fatal (degraded source, never an error).
- Enrichment is cached (snapshots are durable) and bounded (per-provider timeout,
  runs concurrently). Re-resolve reuses cached snapshots — no repeat fan-out
  within the snapshot TTL.
- Expose `GET /api/v1/{entity}/{id}/sources` → `MetadataSourceView[]` for the
  Metadata Sources panel. The merged canonical row still displays Spotify-first.

## Phase 4 — Stats aggregation

- During enrichment, extract engagement metrics from each provider's payload into
  `entity_stat` rows: Spotify `followers`/`popularity`, Deezer `nb_fan`/`rank`,
  YouTube `view_count`, and (new provider) Last.fm `listeners`/`playcount`.
- Add a **Last.fm metadata provider** (free API key, `SPOTDL_LASTFM_API_KEY`;
  absent → silently skipped, a degraded source at most). It contributes
  listeners/playcount + tags(genres) + bio for artists/tracks.
- `EntityStatView` exposes the latest value per (provider, metric) plus the
  captured series for a sparkline. UI: a "Stats" card (songstats-style) — real
  numbers, each with its source badge; a one-line honest note that stream counts
  are provider-reported reach metrics, not licensed play counts.

## Phase 5 — Screen rebuild (web + TUI)

Rebuild every surface on the new system, matching the approved mockups:
- **Web routes:** search (sectioned), track, album, artist, playlist, downloads/
  queue, library, settings, account/auth, admin — plus the nav rail, ⌘K palette,
  top bar, hero backdrops, VU gauges, audio-features/stats panels, metadata-
  sources panel, discography grid.
- **TUI screens:** same information architecture with the NavRail + StatusBar,
  cover-art bitmaps, MatchBar VU, AudioMeter, StatChip, sectioned search,
  discography TabbedContent, stats panel; fix the reference's unstyled
  settings-nav gap.

## Non-goals
- No licensed/scraped true stream counts (Spotify streams, Apple plays) — not
  available via free APIs; the Stats panel shows only provider-reported metrics.
- No new entity type for EP/single — `album_type` is a display label only.
- No lyrics submission changes; no OAuth-in-terminal (unchanged from prior spec).
