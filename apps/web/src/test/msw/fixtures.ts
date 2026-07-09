// Typed MSW fixtures — DEFERRED to Task 2.
//
// The brief requires the fixtures (ConfigResponse, TrackOut, MatchesResponse,
// LyricsResponse, DownloadListResponse, TokenResponse, AdminStatsResponse) to be
// typed against `src/api/generated/types.gen.ts` so a server schema change breaks
// them at compile time. That generated file is produced in Task 2 (which waits on
// Plan 7's final openapi.json), and Task 1 must NOT depend on the generated client.
//
// This placeholder keeps the harness path (src/test/msw/fixtures.ts) reserved.
// Task 2 replaces it with the typed builders and wires the default handlers.
export {};
