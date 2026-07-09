// Typed MSW fixtures (CONTRACT — Task 1 MSW harness, realized in Task 3).
//
// Every builder is typed against the GENERATED `types.gen.ts`, so a server
// schema change breaks these fixtures at compile time (the point of the
// generated-client discipline). Builders take a shallow `overrides` partial.
import type {
  AdminStatsResponse,
  AdminUserResponse,
  ConfigResponse,
  DeploymentMode,
  DownloadDefaults,
  DownloadListResponse,
  LyricsResponse,
  MatchesResponse,
  MatchOut,
  PagedReports,
  PagedUsers,
  ReportResponse,
  TokenResponse,
  TrackOut,
  UserResponse,
} from "../../api/generated/types.gen";

type Overrides<T> = Partial<T>;

// Per-mode feature flags matching Plan 5/6/7's computed defaults (CONTRACT G).
const MODE_FLAGS: Record<DeploymentMode, ConfigResponse["features"]> = {
  hosted: { downloads: false, library: false, auth: true, voting: true },
  selfhost: { downloads: true, library: true, auth: true, voting: true },
  embedded: { downloads: true, library: true, auth: false, voting: false },
};

export function makeConfig(
  overrides: Overrides<ConfigResponse> & { mode?: DeploymentMode } = {},
): ConfigResponse {
  const mode = overrides.mode ?? "selfhost";
  return {
    mode,
    features: overrides.features ?? MODE_FLAGS[mode],
    matcher_version: "1.0.0",
    oauth_providers: [],
    download_defaults: null,
    ...overrides,
  };
}

export function makeDownloadDefaults(
  overrides: Overrides<DownloadDefaults> = {},
): DownloadDefaults {
  return {
    add_unavailable: false,
    bitrate: "auto",
    concurrency: 4,
    create_skip_file: false,
    detect_formats: ["mp3"],
    id3_separator: "/",
    max_filename_length: null,
    output_format: "mp3",
    output_template: "{artists} - {title}.{output-ext}",
    playlist_numbering: false,
    respect_skip_file: true,
    restrict: "none",
    retain_track_cover: false,
    scan_existing: true,
    skip_explicit: false,
    ...overrides,
  };
}

export function makeUser(overrides: Overrides<UserResponse> = {}): UserResponse {
  return {
    id: "user-1",
    email: "user@example.com",
    display_name: "Test User",
    is_admin: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeTrack(overrides: Overrides<TrackOut> = {}): TrackOut {
  return {
    id: "track-1",
    name: "Get Lucky",
    artists: ["Daft Punk", "Pharrell Williams"],
    duration_ms: 248_000,
    album: {
      id: "album-1",
      name: "Random Access Memories",
      cover_url: "https://example.com/cover.jpg",
    },
    year: 2013,
    ...overrides,
  };
}

export function makeMatch(overrides: Overrides<MatchOut> = {}): MatchOut {
  return {
    id: "match-1",
    candidate_name: "Get Lucky (Official Audio)",
    candidate_artists: ["Daft Punk"],
    candidate_duration_ms: 248_000,
    score: 0.94,
    status: "auto",
    matcher_version: "1.0.0",
    net_score: 3,
    upvotes: 4,
    downvotes: 1,
    target_id: "yt-abc123",
    target_provider: "youtube",
    target_url: "https://youtube.com/watch?v=abc123",
    ...overrides,
  };
}

export function makeMatches(
  overrides: Overrides<MatchesResponse> = {},
): MatchesResponse {
  return {
    track_id: "track-1",
    matches: [makeMatch()],
    ...overrides,
  };
}

export function makeLyrics(
  overrides: Overrides<LyricsResponse> = {},
): LyricsResponse {
  return {
    track_id: "track-1",
    lyrics: [
      {
        id: "lyrics-1",
        kind: "plain",
        source: "genius",
        text: "We're up all night to get lucky",
        net_score: 2,
        upvotes: 2,
        downvotes: 0,
      },
    ],
    ...overrides,
  };
}

export function makeDownloadList(
  overrides: Overrides<DownloadListResponse> = {},
): DownloadListResponse {
  return {
    jobs: [],
    total: 0,
    limit: 50,
    offset: 0,
    ...overrides,
  };
}

export function makeToken(
  overrides: Overrides<TokenResponse> = {},
): TokenResponse {
  return {
    access_token: "access-token-1",
    refresh_token: "refresh-token-1",
    token_type: "bearer",
    expires_in: 900,
    user: makeUser(),
    ...overrides,
  };
}

export function makeAdminStats(
  overrides: Overrides<AdminStatsResponse> = {},
): AdminStatsResponse {
  return {
    users_total: 12,
    matches_total: 340,
    community_verified_matches: 88,
    rejected_matches: 5,
    votes_total: 512,
    reports_total: 9,
    reports_pending: 2,
    ...overrides,
  };
}

export function makeAdminUser(
  overrides: Overrides<AdminUserResponse> = {},
): AdminUserResponse {
  return {
    id: "user-1",
    email: "user@example.com",
    display_name: "Test User",
    is_admin: false,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makePagedUsers(overrides: Overrides<PagedUsers> = {}): PagedUsers {
  return {
    items: [makeAdminUser()],
    total: 1,
    ...overrides,
  };
}

export function makeReport(
  overrides: Overrides<ReportResponse> = {},
): ReportResponse {
  return {
    id: "report-1",
    subject_type: "track",
    subject_id: "track-1",
    field: "title",
    proposed_value: "Get Lucky (Radio Edit)",
    reason: "Wrong title",
    status: "pending",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makePagedReports(
  overrides: Overrides<PagedReports> = {},
): PagedReports {
  return {
    items: [makeReport()],
    total: 1,
    ...overrides,
  };
}
