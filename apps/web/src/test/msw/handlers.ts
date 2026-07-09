import type { RequestHandler } from "msw";

// Default MSW handlers. The typed fixtures (ConfigResponse, TrackOut, ...) and
// the default `selfhost` config + sample-track handlers land in Task 2, once the
// generated `src/api/generated/types.gen.ts` exists to type them against (a schema
// change must then break the fixtures at compile time — brief, MSW harness item).
// See fixtures.ts for the deferral note.
export const handlers: RequestHandler[] = [];
