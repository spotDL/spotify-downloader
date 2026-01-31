import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Song } from "@/types";

// API functions
export async function resolveSong(url: string): Promise<Song> {
  const response = await apiClient.get<Song>("/songs/resolve", {
    params: { url },
  });
  return response.data;
}

export async function searchSongs(
  query: string,
  platform?: string,
  limit = 20
): Promise<Song[]> {
  const response = await apiClient.get<Song[]>("/songs/search", {
    params: { q: query, platform, limit },
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
    queryFn: () => resolveSong(url),
    enabled: !!url,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useSearchSongs(query: string, platform?: string, limit = 20) {
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
    mutationFn: resolveSong,
    onSuccess: (song, url) => {
      queryClient.setQueryData(songKeys.resolve(url), song);
      queryClient.setQueryData(songKeys.detail(song.id), song);
    },
  });
}
