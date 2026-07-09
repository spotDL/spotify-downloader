import { useQuery } from "@tanstack/react-query";
// The generated TanStack Query `queryOptions` factories are the ONLY data-fetch
// surface (spec §3). Components consume these app hooks, never the generated SDK
// directly (import-boundary guard, Task 5).
import {
  configApiV1ConfigGetOptions,
  getAlbumApiV1AlbumsIdGetOptions,
  getArtistApiV1ArtistsIdGetOptions,
  getPlaylistApiV1PlaylistsIdGetOptions,
  getTrackApiV1TracksIdGetOptions,
  getTrackLyricsApiV1TracksIdLyricsGetOptions,
  getTrackMatchesApiV1TracksIdMatchesGetOptions,
  searchApiV1SearchGetOptions,
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
