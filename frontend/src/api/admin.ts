/**
 * Admin API client
 *
 * Provides functions and React Query hooks for admin operations:
 * - User management
 * - Match moderation
 * - System statistics
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

export interface ImportMatchesRequest {
  matches: Array<{
    source_url: string;
    source_platform?: string;
    target_url: string;
    target_platform?: string;
    score?: number;
    match_type?: string;
    status?: string;
  }>;
}

export interface BulkUrlImportRequest {
  urls: string[];
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

// Import

export async function importMatches(
  data: ImportMatchesRequest
): Promise<{ message: string; imported: number; skipped: number; errors: string[] }> {
  const response = await apiClient.post<{ message: string; imported: number; skipped: number; errors: string[] }>(
    "/admin/import/matches",
    data
  );
  return response.data;
}

export async function importUrls(
  data: BulkUrlImportRequest
): Promise<{ message: string; resolved: number; skipped: number; errors: string[] }> {
  const response = await apiClient.post<{ message: string; resolved: number; skipped: number; errors: string[] }>(
    "/admin/import/urls",
    data
  );
  return response.data;
}

// Danger Zone

export async function purgeUnverifiedMatches(
  confirm: boolean = false
): Promise<{ message: string; deleted?: number; pending_matches?: number; rejected_matches?: number; total_to_delete?: number }> {
  const response = await apiClient.delete<{ message: string; deleted?: number; pending_matches?: number; rejected_matches?: number; total_to_delete?: number }>(
    `/admin/matches/unverified?confirm=${confirm}`
  );
  return response.data;
}

export async function resetDatabase(
  confirm: string = ""
): Promise<{ message: string; songs_to_delete?: number; matches_to_delete?: number; users_preserved?: boolean }> {
  const response = await apiClient.delete<{ message: string; songs_to_delete?: number; matches_to_delete?: number; users_preserved?: boolean }>(
    `/admin/reset-database?confirm=${confirm}`
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

// Import

export function useImportMatches() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importMatches,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.matches() });
      queryClient.invalidateQueries({ queryKey: ["matches"] });
    },
  });
}

export function useImportUrls() {
  return useMutation({
    mutationFn: importUrls,
  });
}

// Danger Zone

export function usePurgeUnverifiedMatches() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (confirm: boolean) => purgeUnverifiedMatches(confirm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.matches() });
      queryClient.invalidateQueries({ queryKey: adminKeys.stats() });
    },
  });
}

export function useResetDatabase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (confirm: string) => resetDatabase(confirm),
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
}

// ====== Export Functions ======

export interface MatchExportResponse {
  exported_at: string;
  count: number;
  filter_status: string;
  matches: Array<{
    id: string;
    source_url: string;
    source_platform: string;
    target_url: string;
    target_platform: string;
    score: number | null;
    match_type: string;
    status: string;
    upvotes: number;
    downvotes: number;
    net_votes: number;
    created_at: string;
  }>;
}

export interface UserExportResponse {
  exported_at: string;
  count: number;
  users: Array<{
    id: string;
    username: string;
    is_admin: boolean;
    is_active: boolean;
    reputation_score: number;
    matches_submitted: number;
    votes_cast: number;
    reports_submitted: number;
    created_at: string;
  }>;
}

export interface StatisticsExportResponse {
  exported_at: string;
  entities: {
    songs: number;
    artists: number;
    albums: number;
    playlists: number;
    relations: number;
    users: number;
  };
  growth: {
    entities_today: number;
    entities_this_week: number;
    relations_today: number;
    relations_this_week: number;
    new_users_today: number;
    new_users_this_week: number;
  };
  uptime_seconds: number;
  matches_by_status: Record<string, number>;
  users_by_reputation_tier: Record<string, number>;
}

export async function exportMatches(
  status?: MatchStatus
): Promise<MatchExportResponse> {
  const response = await apiClient.get<MatchExportResponse>(
    "/admin/export/matches",
    {
      params: status ? { status } : undefined,
    }
  );
  return response.data;
}

export async function exportUsers(): Promise<UserExportResponse> {
  const response = await apiClient.get<UserExportResponse>("/admin/export/users");
  return response.data;
}

export async function exportStatistics(): Promise<StatisticsExportResponse> {
  const response = await apiClient.get<StatisticsExportResponse>(
    "/admin/export/statistics"
  );
  return response.data;
}

export function useExportMatches() {
  return useMutation({
    mutationFn: (status?: MatchStatus) => exportMatches(status),
  });
}

export function useExportUsers() {
  return useMutation({
    mutationFn: exportUsers,
  });
}

export function useExportStatistics() {
  return useMutation({
    mutationFn: exportStatistics,
  });
}
