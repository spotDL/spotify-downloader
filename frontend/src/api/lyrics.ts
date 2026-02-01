/**
 * Lyrics API hooks and functions.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Lyrics } from "@/types";

// Response types
export interface LyricsResponse {
  song_id: string;
  lyrics_text: string;
  lyrics_synced: string | null;
  source: string;
  from_cache: boolean;
}

export interface LyricsNotFoundResponse {
  song_id: string;
  message: string;
}

// Query keys
export const lyricsKeys = {
  all: ["lyrics"] as const,
  song: (songId: string) => [...lyricsKeys.all, "song", songId] as const,
  search: (name: string, artist: string) =>
    [...lyricsKeys.all, "search", name, artist] as const,
};

/**
 * Get lyrics for a song by its internal ID.
 */
export async function getLyricsForSong(
  songId: string,
  forceRefresh: boolean = false
): Promise<LyricsResponse | LyricsNotFoundResponse> {
  const params = forceRefresh ? { force_refresh: "true" } : {};
  const response = await apiClient.get<LyricsResponse | LyricsNotFoundResponse>(
    `/api/v1/lyrics/song/${songId}`,
    { params }
  );
  return response.data;
}

/**
 * Search for lyrics by song name and artist.
 */
export async function searchLyrics(
  name: string,
  artist: string
): Promise<LyricsResponse | LyricsNotFoundResponse> {
  const response = await apiClient.get<LyricsResponse | LyricsNotFoundResponse>(
    "/api/v1/lyrics/search",
    { params: { name, artist } }
  );
  return response.data;
}

/**
 * Hook to get lyrics for a song.
 */
export function useLyrics(songId: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: lyricsKeys.song(songId ?? ""),
    queryFn: () => getLyricsForSong(songId!),
    enabled: !!songId && (options?.enabled ?? true),
    staleTime: 1000 * 60 * 30, // 30 minutes
  });
}

/**
 * Hook to refresh lyrics from providers.
 */
export function useRefreshLyrics() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (songId: string) => getLyricsForSong(songId, true),
    onSuccess: (data, songId) => {
      queryClient.setQueryData(lyricsKeys.song(songId), data);
    },
  });
}

/**
 * Hook to search for lyrics.
 */
export function useSearchLyrics() {
  return useMutation({
    mutationFn: ({ name, artist }: { name: string; artist: string }) =>
      searchLyrics(name, artist),
  });
}

/**
 * Helper to check if a lyrics response contains lyrics.
 */
export function hasLyrics(
  response: LyricsResponse | LyricsNotFoundResponse
): response is LyricsResponse {
  return "lyrics_text" in response && !!response.lyrics_text;
}

/**
 * Convert API response to Lyrics type for components.
 */
export function toLyrics(response: LyricsResponse): Lyrics {
  return {
    song_id: response.song_id,
    lyrics_text: response.lyrics_text,
    lyrics_synced: response.lyrics_synced,
    source: response.source as Lyrics["source"],
    fetched_at: new Date().toISOString(),
  };
}
