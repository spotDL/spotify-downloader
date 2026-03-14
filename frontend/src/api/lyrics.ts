/**
 * Lyrics API hooks and functions.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Lyrics } from "@/types";

// Response types
export interface LyricsResponse {
  entity_id: string;
  lyrics_text: string;
  lyrics_synced: string | null;
  source: string;
  from_cache: boolean;
}

export interface LyricsNotFoundResponse {
  entity_id: string;
  message: string;
}

// Query keys
export const lyricsKeys = {
  all: ["lyrics"] as const,
  song: (songId: string) => [...lyricsKeys.all, "song", songId] as const,
};

/**
 * Get lyrics for a song by its internal ID.
 */
export async function getLyricsForSong(
  songId: string,
  forceRefresh: boolean = false
): Promise<LyricsResponse | LyricsNotFoundResponse> {
  try {
    const response = await apiClient.get<LyricsResponse | LyricsNotFoundResponse>(
      `/lyrics/entity/${songId}`,
      { params: forceRefresh ? { force_refresh: true } : undefined }
    );
    return response.data;
  } catch {
    return {
      entity_id: songId,
      message: "Failed to fetch lyrics",
    };
  }
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
    entity_id: response.entity_id,
    lyrics_text: response.lyrics_text,
    lyrics_synced: response.lyrics_synced,
    source: response.source as Lyrics["source"],
    fetched_at: new Date().toISOString(),
  };
}
