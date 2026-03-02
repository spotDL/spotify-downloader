import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import {
  listAdminUsers,
  getAdminUser,
  updateAdminUser,
  listAdminMatches,
  updateMatchStatus,
  getSystemStats,
  useAdminUsers,
  useAdminUser,
  useUpdateAdminUser,
  useAdminMatches,
  useUpdateMatchStatus,
  useSystemStats,
  adminKeys,
  type UpdateUserRequest,
  type UpdateMatchStatusRequest,
} from "../../src/api/admin";
import { apiClient } from "../../src/api/client";
import type {
  AdminUser,
  AdminUserListResponse,
  AdminMatch,
  AdminMatchListResponse,
  SystemStats,
} from "../../src/types";

// Mock the API client
vi.mock("../../src/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApiClient = vi.mocked(apiClient);

// Create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("Admin API", () => {
  const mockAdminUser: AdminUser = {
    id: "user-123",
    username: "testadmin",
    email: "admin@example.com",
    is_active: true,
    is_admin: true,
    reputation_score: 500,
    created_at: "2024-01-01T00:00:00Z",
    last_login: "2024-12-01T00:00:00Z",
    matches_submitted: 50,
    votes_cast: 200,
    reports_submitted: 10,
  };

  const mockUserListResponse: AdminUserListResponse = {
    users: [mockAdminUser],
    total: 1,
    page: 1,
    per_page: 20,
    total_pages: 1,
  };

  const mockMatch: AdminMatch = {
    id: "match-123",
    source_url: "https://open.spotify.com/track/abc",
    source_platform: "spotify",
    target_url: "https://youtube.com/watch?v=xyz",
    target_platform: "youtube",
    score: 95,
    confidence: 0.95,
    match_type: "user",
    status: "pending",
    upvotes: 10,
    downvotes: 2,
    net_votes: 8,
    created_at: "2024-12-01T00:00:00Z",
    discovered_by: null,
  };

  const mockMatchListResponse: AdminMatchListResponse = {
    matches: [mockMatch],
    total: 1,
    page: 1,
    per_page: 20,
    total_pages: 1,
  };

  const mockSystemStats: SystemStats = {
    entities: {
      songs: 150000,
      artists: 25000,
      albums: 35000,
      playlists: 5000,
      relations: 200000,
      users: 1500,
    },
    growth: {
      entities_today: 150,
      entities_this_week: 1200,
      relations_today: 250,
      relations_this_week: 2000,
      new_users_today: 25,
      new_users_this_week: 180,
    },
    uptime_seconds: 86400,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("adminKeys", () => {
    it("should generate correct all key", () => {
      expect(adminKeys.all).toEqual(["admin"]);
    });

    it("should generate correct users key", () => {
      expect(adminKeys.users()).toEqual(["admin", "users"]);
    });

    it("should generate correct usersList key", () => {
      const params = { page: 1, per_page: 20 };
      expect(adminKeys.usersList(params)).toEqual([
        "admin",
        "users",
        "list",
        params,
      ]);
    });

    it("should generate correct user key", () => {
      expect(adminKeys.user("user-123")).toEqual(["admin", "users", "user-123"]);
    });

    it("should generate correct matches key", () => {
      expect(adminKeys.matches()).toEqual(["admin", "matches"]);
    });

    it("should generate correct matchesList key", () => {
      const params = { page: 1, status: "pending" as const };
      expect(adminKeys.matchesList(params)).toEqual([
        "admin",
        "matches",
        "list",
        params,
      ]);
    });

    it("should generate correct stats key", () => {
      expect(adminKeys.stats()).toEqual(["admin", "stats"]);
    });
  });

  describe("listAdminUsers", () => {
    it("should fetch users with default params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockUserListResponse });

      const result = await listAdminUsers();

      expect(mockApiClient.get).toHaveBeenCalledWith("/admin/users", {
        params: {
          page: 1,
          per_page: 20,
          search: undefined,
          is_admin: undefined,
          is_active: undefined,
          sort_by: "created_at",
          sort_order: "desc",
        },
      });
      expect(result).toEqual(mockUserListResponse);
    });

    it("should fetch users with custom params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockUserListResponse });

      await listAdminUsers({
        page: 2,
        per_page: 10,
        search: "admin",
        is_admin: true,
        sort_by: "username",
        sort_order: "asc",
      });

      expect(mockApiClient.get).toHaveBeenCalledWith("/admin/users", {
        params: {
          page: 2,
          per_page: 10,
          search: "admin",
          is_admin: true,
          is_active: undefined,
          sort_by: "username",
          sort_order: "asc",
        },
      });
    });

    it("should throw error on API failure", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      await expect(listAdminUsers()).rejects.toThrow("Fetch failed");
    });
  });

  describe("getAdminUser", () => {
    it("should fetch a single user by ID", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockAdminUser });

      const result = await getAdminUser("user-123");

      expect(mockApiClient.get).toHaveBeenCalledWith("/admin/users/user-123");
      expect(result).toEqual(mockAdminUser);
    });

    it("should throw error on API failure", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Not found"));

      await expect(getAdminUser("invalid-id")).rejects.toThrow("Not found");
    });
  });

  describe("updateAdminUser", () => {
    it("should update user properties", async () => {
      const updatedUser = { ...mockAdminUser, is_admin: false };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedUser });

      const updateData: UpdateUserRequest = { is_admin: false };
      const result = await updateAdminUser("user-123", updateData);

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/admin/users/user-123",
        updateData
      );
      expect(result.is_admin).toBe(false);
    });

    it("should update multiple properties", async () => {
      const updatedUser = {
        ...mockAdminUser,
        is_active: false,
        reputation_score: 100,
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedUser });

      const updateData: UpdateUserRequest = {
        is_active: false,
        reputation_score: 100,
      };
      await updateAdminUser("user-123", updateData);

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/admin/users/user-123",
        updateData
      );
    });

    it("should throw error on API failure", async () => {
      mockApiClient.patch.mockRejectedValueOnce(new Error("Update failed"));

      await expect(
        updateAdminUser("user-123", { is_admin: false })
      ).rejects.toThrow("Update failed");
    });
  });

  describe("listAdminMatches", () => {
    it("should fetch matches with default params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockMatchListResponse });

      const result = await listAdminMatches();

      expect(mockApiClient.get).toHaveBeenCalledWith("/admin/matches", {
        params: {
          page: 1,
          per_page: 20,
          status: undefined,
          match_type: undefined,
        },
      });
      expect(result).toEqual(mockMatchListResponse);
    });

    it("should fetch matches with filters", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockMatchListResponse });

      await listAdminMatches({
        page: 1,
        status: "pending",
        match_type: "user",
      });

      expect(mockApiClient.get).toHaveBeenCalledWith("/admin/matches", {
        params: {
          page: 1,
          per_page: 20,
          status: "pending",
          match_type: "user",
        },
      });
    });

    it("should throw error on API failure", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      await expect(listAdminMatches()).rejects.toThrow("Fetch failed");
    });
  });

  describe("updateMatchStatus", () => {
    it("should update match status", async () => {
      const updatedMatch = { ...mockMatch, status: "verified" as const };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedMatch });

      const updateData: UpdateMatchStatusRequest = { status: "verified" };
      const result = await updateMatchStatus("match-123", updateData);

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/admin/matches/match-123",
        updateData
      );
      expect(result).toEqual(updatedMatch);
    });

    it("should throw error on API failure", async () => {
      mockApiClient.patch.mockRejectedValueOnce(new Error("Update failed"));

      await expect(
        updateMatchStatus("match-123", { status: "rejected" })
      ).rejects.toThrow("Update failed");
    });
  });

  describe("getSystemStats", () => {
    it("should fetch system stats", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockSystemStats });

      const result = await getSystemStats();

      expect(mockApiClient.get).toHaveBeenCalledWith("/admin/stats");
      expect(result).toEqual(mockSystemStats);
    });

    it("should throw error on API failure", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      await expect(getSystemStats()).rejects.toThrow("Fetch failed");
    });
  });

  describe("useAdminUsers hook", () => {
    it("should fetch users list", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockUserListResponse });

      const { result } = renderHook(() => useAdminUsers(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockUserListResponse);
    });

    it("should fetch with custom params", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockUserListResponse });

      const { result } = renderHook(
        () => useAdminUsers({ page: 2, is_admin: true }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("should handle error", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      const { result } = renderHook(() => useAdminUsers(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useAdminUser hook", () => {
    it("should fetch a single user", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockAdminUser });

      const { result } = renderHook(() => useAdminUser("user-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAdminUser);
    });

    it("should not fetch when user ID is empty", async () => {
      const { result } = renderHook(() => useAdminUser(""), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe("useUpdateAdminUser hook", () => {
    it("should update user", async () => {
      const updatedUser = { ...mockAdminUser, is_admin: false };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedUser });

      const { result } = renderHook(() => useUpdateAdminUser(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        userId: "user-123",
        data: { is_admin: false },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/admin/users/user-123",
        { is_admin: false }
      );
    });

    it("should handle update error", async () => {
      mockApiClient.patch.mockRejectedValueOnce(new Error("Update failed"));

      const { result } = renderHook(() => useUpdateAdminUser(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        userId: "user-123",
        data: { is_admin: false },
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useAdminMatches hook", () => {
    it("should fetch matches list", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockMatchListResponse });

      const { result } = renderHook(() => useAdminMatches(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockMatchListResponse);
    });

    it("should fetch with filters", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockMatchListResponse });

      const { result } = renderHook(
        () => useAdminMatches({ status: "pending", match_type: "user" }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("useUpdateMatchStatus hook", () => {
    it("should update match status", async () => {
      const updatedMatch = { ...mockMatch, status: "verified" as const };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedMatch });

      const { result } = renderHook(() => useUpdateMatchStatus(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        matchId: "match-123",
        data: { status: "verified" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        "/admin/matches/match-123",
        { status: "verified" }
      );
    });

    it("should handle update error", async () => {
      mockApiClient.patch.mockRejectedValueOnce(new Error("Update failed"));

      const { result } = renderHook(() => useUpdateMatchStatus(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        matchId: "match-123",
        data: { status: "rejected" },
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("useSystemStats hook", () => {
    it("should fetch system stats", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockSystemStats });

      const { result } = renderHook(() => useSystemStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockSystemStats);
    });

    it("should handle error", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      const { result } = renderHook(() => useSystemStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });
});
