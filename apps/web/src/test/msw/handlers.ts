import { http, HttpResponse } from "msw";
import { makeConfig, makeTrack } from "./fixtures";

// Default MSW handlers: a `selfhost` config + a sample track. Individual tests
// override these with `server.use(...)`. Paths use a `*` origin prefix so they
// match the same-origin (`/api/v1/...`) requests the generated client issues in
// jsdom regardless of the test `location`.
export const handlers = [
  http.get("*/api/v1/config", () => HttpResponse.json(makeConfig())),
  http.get("*/api/v1/tracks/:id", ({ params }) =>
    HttpResponse.json(makeTrack({ id: String(params.id) })),
  ),
];
