import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Song } from "@/types";

// Helper to detect if input is a URL
export function isValidUrl(input: string): boolean {
  try {
    const url = new URL(input);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export interface SearchResponse {
  songs: Song[];
  total: number;
}

export interface ResolveResponse {
  songs: Song[];
  total: number;
}

export async function searchSongs(
  query: string,
  platform = "spotify",
  limit = 20
): Promise<SearchResponse> {
  const response = await apiClient.get<SearchResponse>("/songs/search", {
    params: { query, platform, limit },
  });
  return response.data;
}

export async function resolveSongUrl(url: string): Promise<ResolveResponse> {
  const response = await apiClient.get<ResolveResponse>("/songs/resolve", {
    params: { url },
  });
  return response.data;
}

export async function getSong(id: string): Promise<Song> {
  const response = await apiClient.get<Song>(`/songs/${id}`);
  return response.data;
}

// Query keys
export const songKeys = {
  all: ["songs"] as const,
  lists: () => [...songKeys.all, "list"] as const,
  list: (filters: { query?: string; platform?: string }) =>
    [...songKeys.lists(), filters] as const,
  details: () => [...songKeys.all, "detail"] as const,
  detail: (id: string) => [...songKeys.details(), id] as const,
  resolve: (url: string) => [...songKeys.all, "resolve", url] as const,
};

// Hooks
export function useResolveSong(url: string) {
  return useQuery({
    queryKey: songKeys.resolve(url),
    queryFn: () => resolveSongUrl(url),
    enabled: !!url && isValidUrl(url),
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useSearchSongs(query: string, platform = "spotify", limit = 20) {
  return useQuery({
    queryKey: songKeys.list({ query, platform }),
    queryFn: () => searchSongs(query, platform, limit),
    enabled: query.length > 0,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useSong(id: string) {
  return useQuery({
    queryKey: songKeys.detail(id),
    queryFn: () => getSong(id),
    enabled: !!id,
  });
}

export function useResolveSongMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resolveSongUrl,
    onSuccess: (response, url) => {
      queryClient.setQueryData(songKeys.resolve(url), response);
      // Cache individual songs by platform_id
      for (const song of response.songs) {
        queryClient.setQueryData(songKeys.detail(song.platform_id), song);
      }
    },
  });
}

export function useSearchSongsMutation() {
  return useMutation({
    mutationFn: ({
      query,
      platform = "spotify",
      limit = 20,
    }: {
      query: string;
      platform?: string;
      limit?: number;
    }) => searchSongs(query, platform, limit),
  });
}
