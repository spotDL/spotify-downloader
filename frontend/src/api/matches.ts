import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { Match, MatchResult, FindMatchesRequest, FindMatchesResponse } from "@/types";

// API functions
export async function findMatches(
  sourceUrl: string,
  targetPlatforms: string[]
): Promise<FindMatchesResponse> {
  const response = await apiClient.post<FindMatchesResponse>("/matches/find", {
    source_url: sourceUrl,
    target_platforms: targetPlatforms,
  } satisfies FindMatchesRequest);
  return response.data;
}

export async function getMatch(id: string): Promise<Match> {
  const response = await apiClient.get<Match>(`/matches/${id}`);
  return response.data;
}

export interface SubmitMatchRequest {
  source_url: string;
  target_url: string;
  target_platform: string;
}

export interface MatchPreviewResponse {
  target_url: string;
  target_platform: string;
  result: MatchResult;
}

export async function submitMatch(data: SubmitMatchRequest): Promise<Match> {
  const response = await apiClient.post<Match>("/matches/submit", data);
  return response.data;
}

export async function previewMatchUrl(targetUrl: string): Promise<MatchPreviewResponse> {
  const response = await apiClient.get<MatchPreviewResponse>("/matches/preview", {
    params: {
      target_url: targetUrl,
    },
  });
  return response.data;
}

export async function getMatchesForSong(songId: string): Promise<Match[]> {
  const response = await apiClient.get<Match[]>(`/songs/${songId}/matches`);
  return response.data;
}

// Query keys
export const matchKeys = {
  all: ["matches"] as const,
  lists: () => [...matchKeys.all, "list"] as const,
  list: (filters: { songId?: string }) =>
    [...matchKeys.lists(), filters] as const,
  details: () => [...matchKeys.all, "detail"] as const,
  detail: (id: string) => [...matchKeys.details(), id] as const,
  find: (sourceUrl: string, platforms: string[]) =>
    [...matchKeys.all, "find", sourceUrl, platforms] as const,
  preview: (targetUrl: string) => [...matchKeys.all, "preview", targetUrl] as const,
};

// Hooks
export function useFindMatches(
  sourceUrl: string,
  targetPlatforms: string[],
  enabled = true
) {
  return useQuery({
    queryKey: matchKeys.find(sourceUrl, targetPlatforms),
    queryFn: () => findMatches(sourceUrl, targetPlatforms),
    enabled: enabled && !!sourceUrl && targetPlatforms.length > 0,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

export function useMatch(id: string) {
  return useQuery({
    queryKey: matchKeys.detail(id),
    queryFn: () => getMatch(id),
    enabled: !!id,
  });
}

export function useMatchPreview(targetUrl: string, enabled = true) {
  return useQuery({
    queryKey: matchKeys.preview(targetUrl),
    queryFn: () => previewMatchUrl(targetUrl),
    enabled: enabled && !!targetUrl,
    retry: false,
  });
}

export function useMatchesForSong(songId: string) {
  return useQuery({
    queryKey: matchKeys.list({ songId }),
    queryFn: () => getMatchesForSong(songId),
    enabled: !!songId,
  });
}

export function useFindMatchesMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sourceUrl,
      targetPlatforms,
    }: {
      sourceUrl: string;
      targetPlatforms: string[];
    }) => findMatches(sourceUrl, targetPlatforms),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(
        matchKeys.find(variables.sourceUrl, variables.targetPlatforms),
        data
      );
    },
  });
}

export function useSubmitMatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: submitMatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: matchKeys.all });
    },
  });
}
