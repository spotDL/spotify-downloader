import { http, HttpResponse } from "msw";
import {
  makeConfig,
  makeLyrics,
  makeMatches,
  makeSources,
  makeTrack,
} from "./fixtures";

// Default MSW handlers: a `selfhost` config + a sample track (plus its matches
// and lyrics, so any track-page render resolves without per-test setup).
// Individual tests override these with `server.use(...)`. Paths use a `*` origin
// prefix so they match the same-origin (`/api/v1/...`) requests the generated
// client issues in jsdom regardless of the test `location`.
export const handlers = [
  http.get("*/api/v1/config", () => HttpResponse.json(makeConfig())),
  http.get("*/api/v1/tracks/:id/matches", ({ params }) =>
    HttpResponse.json(makeMatches({ track_id: String(params.id) })),
  ),
  http.get("*/api/v1/tracks/:id/lyrics", ({ params }) =>
    HttpResponse.json(makeLyrics({ track_id: String(params.id) })),
  ),
  http.get("*/api/v1/tracks/:id", ({ params }) =>
    HttpResponse.json(makeTrack({ id: String(params.id) })),
  ),
  // Cross-provider provenance (`SourcesPanel` / `StatsCard`). One default per
  // entity type so any detail-page render resolves without per-test setup.
  http.get("*/api/v1/artists/:id/sources", ({ params }) =>
    HttpResponse.json(makeSources({ entity_type: "artist", entity_id: String(params.id) })),
  ),
  http.get("*/api/v1/albums/:id/sources", ({ params }) =>
    HttpResponse.json(makeSources({ entity_type: "album", entity_id: String(params.id) })),
  ),
  http.get("*/api/v1/tracks/:id/sources", ({ params }) =>
    HttpResponse.json(makeSources({ entity_type: "track", entity_id: String(params.id) })),
  ),
  http.get("*/api/v1/playlists/:id/sources", ({ params }) =>
    HttpResponse.json(makeSources({ entity_type: "playlist", entity_id: String(params.id) })),
  ),
];
