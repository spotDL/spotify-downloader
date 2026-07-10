import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
// The generated TanStack Query `queryOptions`/`mutation` factories are the ONLY
// data-fetch surface (spec §3). Components consume these app hooks, never the
// generated SDK directly (import-boundary guard, Task 5).
import {
  configApiV1ConfigGetOptions,
  createReportApiV1ReportsPostMutation,
  getAlbumApiV1AlbumsIdGetOptions,
  getAlbumSourcesApiV1AlbumsIdSourcesGetOptions,
  getArtistApiV1ArtistsIdGetOptions,
  getArtistApiV1ArtistsIdGetQueryKey,
  getArtistSourcesApiV1ArtistsIdSourcesGetOptions,
  getArtistSourcesApiV1ArtistsIdSourcesGetQueryKey,
  getPlaylistApiV1PlaylistsIdGetOptions,
  getPlaylistSourcesApiV1PlaylistsIdSourcesGetOptions,
  getTrackApiV1TracksIdGetOptions,
  getTrackSourcesApiV1TracksIdSourcesGetOptions,
  getTrackApiV1TracksIdGetQueryKey,
  getTrackLyricsApiV1TracksIdLyricsGetOptions,
  getTrackLyricsApiV1TracksIdLyricsGetQueryKey,
  getTrackMatchesApiV1TracksIdMatchesGetOptions,
  getTrackMatchesApiV1TracksIdMatchesGetQueryKey,
  listDownloadsApiV1DownloadsGetQueryKey,
  meApiV1AuthMeGetOptions,
  resolveApiV1ResolvePostMutation,
  searchApiV1SearchGetOptions,
  submitDownloadApiV1DownloadsPostMutation,
  submitMatchApiV1TracksIdMatchesPostMutation,
  voteLyricsApiV1LyricsLyricsIdVotePostMutation,
  voteMatchApiV1MatchesMatchIdVotePostMutation,
} from "./generated/@tanstack/react-query.gen";
// Admin + health surfaces have no generated `queryOptions` we want to key by
// operation name — the admin views invalidate by the stable `["admin", …]`
// prefixes below, so these hooks call the generated SDK operations directly
// (this app-hook module IS the boundary; components still never touch the SDK).
import {
  approveReportApiV1AdminReportsReportIdApprovePost,
  healthApiV1HealthGet,
  listUsersApiV1AdminUsersGet,
  rejectReportApiV1AdminReportsReportIdRejectPost,
  reportsQueueApiV1AdminReportsGet,
  statsApiV1AdminStatsGet,
} from "./generated/sdk.gen";
import type { EntityType, ReportStatus } from "./generated/types.gen";
import { resolveHttpBase } from "./client";
import { useAuthStore } from "../stores/auth";

/**
 * `GET /config` — fetched once at boot (CONTRACT G). `staleTime: Infinity` (the
 * server config is startup-fixed, spec §4) and `retry: false` so the ConfigGate
 * surfaces the recovery screen immediately rather than after backoff.
 */
export function useConfig() {
  return useQuery({
    ...configApiV1ConfigGetOptions(),
    staleTime: Infinity,
    retry: false,
  });
}

/** `GET /search?q=&limit=` — disabled until the query is non-empty (CONTRACT D). */
export function useSearch(q: string, limit?: number) {
  const query = q.trim();
  return useQuery({
    ...searchApiV1SearchGetOptions({
      query: limit === undefined ? { q: query } : { q: query, limit },
    }),
    enabled: query.length > 0,
  });
}

export function useTrack(id: string) {
  return useQuery({
    ...getTrackApiV1TracksIdGetOptions({ path: { id } }),
    enabled: id.length > 0,
  });
}

export function useAlbum(id: string) {
  return useQuery({
    ...getAlbumApiV1AlbumsIdGetOptions({ path: { id } }),
    enabled: id.length > 0,
  });
}

export function useArtist(id: string) {
  return useQuery({
    ...getArtistApiV1ArtistsIdGetOptions({ path: { id } }),
    enabled: id.length > 0,
  });
}

export function usePlaylist(id: string) {
  return useQuery({
    ...getPlaylistApiV1PlaylistsIdGetOptions({ path: { id } }),
    enabled: id.length > 0,
  });
}

/**
 * `GET /{tracks|albums|artists|playlists}/{id}/sources` — the per-provider
 * provenance behind a canonical entity (the "Metadata sources" panel + reach
 * stats). Picks the right generated endpoint by `entityType`; all four return
 * the same `SourcesResponse`. Disabled until an id is present.
 */
export function useEntitySources(entityType: EntityType, id: string) {
  const path = { path: { id } };
  const options =
    entityType === "artist"
      ? getArtistSourcesApiV1ArtistsIdSourcesGetOptions(path)
      : entityType === "album"
        ? getAlbumSourcesApiV1AlbumsIdSourcesGetOptions(path)
        : entityType === "playlist"
          ? getPlaylistSourcesApiV1PlaylistsIdSourcesGetOptions(path)
          : getTrackSourcesApiV1TracksIdSourcesGetOptions(path);
  return useQuery({ ...options, enabled: id.length > 0 });
}

/**
 * Force-refresh a canonical artist from its providers.
 *
 * A resolved artist's snapshots are permanent, so a plain refetch re-reads the
 * same DB row forever. This resolves the artist's Spotify-first source ref with
 * `force: true` (bypassing the snapshot cache server-side), then invalidates the
 * artist + sources queries. Falls back to a plain invalidate when the sources
 * are not loaded yet (e.g. right after mount).
 */
export function useForceRefreshArtist(artistId: string) {
  const queryClient = useQueryClient();
  const sources = useEntitySources("artist", artistId);
  const resolve = useResolve();

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: getArtistApiV1ArtistsIdGetQueryKey({ path: { id: artistId } }),
    });
    void queryClient.invalidateQueries({
      queryKey: getArtistSourcesApiV1ArtistsIdSourcesGetQueryKey({ path: { id: artistId } }),
    });
  };

  const refresh = () => {
    const source = sources.data?.sources?.[0]; // Spotify-first ordering
    if (!source) {
      invalidate();
      return;
    }
    resolve.mutate(
      { body: { query: `${source.provider}:artist:${source.provider_entity_id}`, force: true } },
      { onSuccess: invalidate, onError: invalidate },
    );
  };

  return { refresh, refreshing: resolve.isPending };
}

/**
 * Returns a callback that invalidates a track's three server-state queries
 * (metadata, matches, lyrics) so the "Refresh metadata" action re-reads them all.
 */
export function useRefreshTrack(id: string) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({
      queryKey: getTrackApiV1TracksIdGetQueryKey({ path: { id } }),
    });
    void queryClient.invalidateQueries({
      queryKey: getTrackMatchesApiV1TracksIdMatchesGetQueryKey({ path: { id } }),
    });
    void queryClient.invalidateQueries({
      queryKey: getTrackLyricsApiV1TracksIdLyricsGetQueryKey({ path: { id } }),
    });
  };
}

export function useTrackMatches(id: string) {
  return useQuery({
    ...getTrackMatchesApiV1TracksIdMatchesGetOptions({ path: { id } }),
    enabled: id.length > 0,
  });
}

export function useTrackLyrics(id: string) {
  return useQuery({
    ...getTrackLyricsApiV1TracksIdLyricsGetOptions({ path: { id } }),
    enabled: id.length > 0,
  });
}

// --- Mutations (CONTRACT D) ---------------------------------------------------
// Each mutation invalidates exactly the server-state queries its write affects,
// so the UI re-reads fresh data instead of hand-patching the cache.

/** `POST /resolve` — a URL/ref/free-text → tagged entity (no cache to touch). */
export function useResolve() {
  return useMutation(resolveApiV1ResolvePostMutation());
}

/**
 * `POST /reports` — file a metadata-correction report against a canonical entity
 * (the track/album/artist "Report" action). Append-only server-side, so there's
 * no client cache to invalidate.
 */
export function useSubmitReport() {
  return useMutation(createReportApiV1ReportsPostMutation());
}

/**
 * `POST /matches/{id}/vote` — up/down/retract a match vote. On success the
 * track's ranked match list is stale (tallies + derived status changed), so we
 * invalidate `["track", trackId, "matches"]`.
 */
export function useVoteMatch(trackId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    ...voteMatchApiV1MatchesMatchIdVotePostMutation(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: getTrackMatchesApiV1TracksIdMatchesGetQueryKey({
          path: { id: trackId },
        }),
      }),
  });
}

/** `POST /lyrics/{id}/vote` — invalidates the track's lyrics variants. */
export function useVoteLyrics(trackId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    ...voteLyricsApiV1LyricsLyricsIdVotePostMutation(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: getTrackLyricsApiV1TracksIdLyricsGetQueryKey({
          path: { id: trackId },
        }),
      }),
  });
}

/** `POST /tracks/{id}/matches` — submit a community match URL; refresh matches. */
export function useSubmitMatch(trackId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    ...submitMatchApiV1TracksIdMatchesPostMutation(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: getTrackMatchesApiV1TracksIdMatchesGetQueryKey({
          path: { id: trackId },
        }),
      }),
  });
}

/** `POST /downloads` — enqueue a batch; invalidates the downloads list. */
export function useEnqueueDownload() {
  const queryClient = useQueryClient();
  return useMutation({
    ...submitDownloadApiV1DownloadsPostMutation(),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: listDownloadsApiV1DownloadsGetQueryKey(),
      }),
  });
}

/**
 * `GET /auth/me` query options (CONTRACT C/G). Shared verbatim between `useMe`
 * (nav/settings) and the admin route's `beforeLoad` guard so both read/write the
 * one ["me"] cache entry — the guard's `ensureQueryData` warms exactly what the
 * hook then renders. The authenticated profile & `is_admin` live here (server
 * state), never in the auth store.
 */
export function meQueryOptions() {
  return meApiV1AuthMeGetOptions();
}

/** `GET /auth/me` — disabled until an access token exists (no point 401ing). */
export function useMe() {
  const accessToken = useAuthStore((s) => s.accessToken);
  return useQuery({ ...meQueryOptions(), enabled: accessToken !== null });
}

/**
 * Probe the API's health endpoint at the *currently configured* base URL
 * (CONTRACT B): `{resolveHttpBase()}/api/v1/health` (same-origin when the
 * override is blank). Used by Settings' "test connection". Returns `true` only
 * on a 2xx; any HTTP error or network/parse failure is `false`.
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const { error } = await healthApiV1HealthGet({
      baseUrl: resolveHttpBase(),
      throwOnError: false,
    });
    return !error;
  } catch {
    return false;
  }
}

// Stable admin query-key prefixes (CONTRACT G). Approve/reject invalidate by the
// `["admin", "reports"]` / `["admin", "stats"]` prefixes, so every status filter
// and the stats cards refetch after a review without naming each variant.
const ADMIN_REPORTS_KEY = ["admin", "reports"] as const;
const ADMIN_STATS_KEY = ["admin", "stats"] as const;
const ADMIN_USERS_KEY = ["admin", "users"] as const;

/** `GET /admin/stats` — aggregate community-health counts for the dashboard. */
export function useAdminStats() {
  return useQuery({
    queryKey: ADMIN_STATS_KEY,
    queryFn: async ({ signal }) => {
      const { data } = await statsApiV1AdminStatsGet({ signal, throwOnError: true });
      return data;
    },
  });
}

/** `GET /admin/reports?status=` — the review queue filtered by status. */
export function useAdminReports(status: ReportStatus) {
  return useQuery({
    queryKey: [...ADMIN_REPORTS_KEY, status],
    queryFn: async ({ signal }) => {
      const { data } = await reportsQueueApiV1AdminReportsGet({
        query: { status },
        signal,
        throwOnError: true,
      });
      return data;
    },
  });
}

/** `GET /admin/users?limit=&offset=` — a page of users plus the total count. */
export function useAdminUsers(page: { limit: number; offset: number }) {
  return useQuery({
    queryKey: [...ADMIN_USERS_KEY, page],
    queryFn: async ({ signal }) => {
      const { data } = await listUsersApiV1AdminUsersGet({
        query: page,
        signal,
        throwOnError: true,
      });
      return data;
    },
  });
}

type ReviewVars = { reportId: string; note?: string };

// Approve/reject share the post-review invalidation: the queue (any status) and
// the stats cards are now stale. The verb is the route, not a field.
function useReviewReport(
  submit: (vars: ReviewVars) => Promise<unknown>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: submit,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ADMIN_REPORTS_KEY });
      void queryClient.invalidateQueries({ queryKey: ADMIN_STATS_KEY });
    },
  });
}

/** `POST /admin/reports/{id}/approve` — records approval; refetches queue+stats. */
export function useApproveReport() {
  return useReviewReport(({ reportId, note }) =>
    approveReportApiV1AdminReportsReportIdApprovePost({
      path: { report_id: reportId },
      body: { note: note ?? null },
      throwOnError: true,
    }),
  );
}

/** `POST /admin/reports/{id}/reject` — records rejection; refetches queue+stats. */
export function useRejectReport() {
  return useReviewReport(({ reportId, note }) =>
    rejectReportApiV1AdminReportsReportIdRejectPost({
      path: { report_id: reportId },
      body: { note: note ?? null },
      throwOnError: true,
    }),
  );
}
