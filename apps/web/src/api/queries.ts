import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
// The generated TanStack Query `queryOptions`/`mutation` factories are the ONLY
// data-fetch surface (spec §3). Components consume these app hooks, never the
// generated SDK directly (import-boundary guard, Task 5).
import {
  configApiV1ConfigGetOptions,
  getAlbumApiV1AlbumsIdGetOptions,
  getArtistApiV1ArtistsIdGetOptions,
  getPlaylistApiV1PlaylistsIdGetOptions,
  getTrackApiV1TracksIdGetOptions,
  getTrackLyricsApiV1TracksIdLyricsGetOptions,
  getTrackLyricsApiV1TracksIdLyricsGetQueryKey,
  getTrackMatchesApiV1TracksIdMatchesGetOptions,
  getTrackMatchesApiV1TracksIdMatchesGetQueryKey,
  listDownloadsApiV1DownloadsGetQueryKey,
  resolveApiV1ResolvePostMutation,
  searchApiV1SearchGetOptions,
  submitDownloadApiV1DownloadsPostMutation,
  submitMatchApiV1TracksIdMatchesPostMutation,
  voteLyricsApiV1LyricsLyricsIdVotePostMutation,
  voteMatchApiV1MatchesMatchIdVotePostMutation,
} from "./generated/@tanstack/react-query.gen";

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
