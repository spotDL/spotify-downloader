/**
 * Admin API client
 *
 * Provides functions and React Query hooks for admin operations:
 * - User management
 * - Match moderation
 * - System statistics
 * - Cache management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  AdminUser,
  AdminUserListRequest,
  AdminUserListResponse,
  AdminMatchListRequest,
  AdminMatchListResponse,
  SystemStats,
  Match,
} from "@/types";

// ====== API Functions ======

export type MatchStatus = "pending" | "verified" | "rejected";

export interface UpdateUserRequest {
  is_active?: boolean;
  is_admin?: boolean;
  reputation_score?: number;
}

export interface UpdateMatchStatusRequest {
  status: MatchStatus;
}

export interface ClearCacheRequest {
  cache_type: "all" | "search" | "entities" | "matches";
}

// Users

export async function listAdminUsers(
  params: AdminUserListRequest = {}
): Promise<AdminUserListResponse> {
  const response = await apiClient.get<AdminUserListResponse>("/admin/users", {
    params: {
      page: params.page || 1,
      per_page: params.per_page || 20,
      search: params.search,
      is_admin: params.is_admin,
      is_active: params.is_active,
      sort_by: params.sort_by || "created_at",
      sort_order: params.sort_order || "desc",
    },
  });
  return response.data;
}

export async function getAdminUser(userId: string): Promise<AdminUser> {
  const response = await apiClient.get<AdminUser>(`/admin/users/${userId}`);
  return response.data;
}

export async function updateAdminUser(
  userId: string,
  data: UpdateUserRequest
): Promise<AdminUser> {
  const response = await apiClient.patch<AdminUser>(
    `/admin/users/${userId}`,
    data
  );
  return response.data;
}

// Matches

export async function listAdminMatches(
  params: AdminMatchListRequest = {}
): Promise<AdminMatchListResponse> {
  const response = await apiClient.get<AdminMatchListResponse>(
    "/admin/matches",
    {
      params: {
        page: params.page || 1,
        per_page: params.per_page || 20,
        status: params.status,
        match_type: params.match_type,
      },
    }
  );
  return response.data;
}

export async function updateMatchStatus(
  matchId: string,
  data: UpdateMatchStatusRequest
): Promise<Match> {
  const response = await apiClient.patch<Match>(
    `/admin/matches/${matchId}`,
    data
  );
  return response.data;
}

// Stats

export async function getSystemStats(): Promise<SystemStats> {
  const response = await apiClient.get<SystemStats>("/admin/stats");
  return response.data;
}

// Cache

export async function clearCache(
  data: ClearCacheRequest
): Promise<{ message: string; cache_type: string }> {
  const response = await apiClient.post<{ message: string; cache_type: string }>(
    "/admin/cache/clear",
    data
  );
  return response.data;
}

// ====== Query Keys ======

export const adminKeys = {
  all: ["admin"] as const,
  users: () => [...adminKeys.all, "users"] as const,
  usersList: (params: AdminUserListRequest) =>
    [...adminKeys.users(), "list", params] as const,
  user: (id: string) => [...adminKeys.users(), id] as const,
  matches: () => [...adminKeys.all, "matches"] as const,
  matchesList: (params: AdminMatchListRequest) =>
    [...adminKeys.matches(), "list", params] as const,
  stats: () => [...adminKeys.all, "stats"] as const,
};

// ====== React Query Hooks ======

// Users

export function useAdminUsers(params: AdminUserListRequest = {}) {
  return useQuery({
    queryKey: adminKeys.usersList(params),
    queryFn: () => listAdminUsers(params),
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useAdminUser(userId: string) {
  return useQuery({
    queryKey: adminKeys.user(userId),
    queryFn: () => getAdminUser(userId),
    enabled: !!userId,
    staleTime: 1000 * 60, // 1 minute
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      data,
    }: {
      userId: string;
      data: UpdateUserRequest;
    }) => updateAdminUser(userId, data),
    onSuccess: (data, variables) => {
      // Update the individual user cache
      queryClient.setQueryData(adminKeys.user(variables.userId), data);
      // Invalidate the users list
      queryClient.invalidateQueries({ queryKey: adminKeys.users() });
    },
  });
}

// Matches

export function useAdminMatches(params: AdminMatchListRequest = {}) {
  return useQuery({
    queryKey: adminKeys.matchesList(params),
    queryFn: () => listAdminMatches(params),
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useUpdateMatchStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      matchId,
      data,
    }: {
      matchId: string;
      data: UpdateMatchStatusRequest;
    }) => updateMatchStatus(matchId, data),
    onSuccess: () => {
      // Invalidate the matches list
      queryClient.invalidateQueries({ queryKey: adminKeys.matches() });
    },
  });
}

// Stats

export function useSystemStats() {
  return useQuery({
    queryKey: adminKeys.stats(),
    queryFn: getSystemStats,
    staleTime: 1000 * 60, // 1 minute
    refetchInterval: 1000 * 60, // Refetch every minute
  });
}

// Cache

export function useClearCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: clearCache,
    onSuccess: (_, variables) => {
      // Invalidate relevant caches based on what was cleared
      if (variables.cache_type === "all") {
        queryClient.invalidateQueries();
      } else if (variables.cache_type === "entities") {
        queryClient.invalidateQueries({ queryKey: ["entities"] });
      } else if (variables.cache_type === "matches") {
        queryClient.invalidateQueries({ queryKey: ["matches"] });
        queryClient.invalidateQueries({ queryKey: adminKeys.matches() });
      } else if (variables.cache_type === "search") {
        queryClient.invalidateQueries({
          queryKey: ["entities", "search"],
        });
      }
    },
  });
}
