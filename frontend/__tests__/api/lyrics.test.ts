import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import {
  getLyricsForSong,
  searchLyrics,
  useLyrics,
  useRefreshLyrics,
  useSearchLyrics,
  hasLyrics,
  toLyrics,
  lyricsKeys,
  type LyricsResponse,
  type LyricsNotFoundResponse,
} from "../../src/api/lyrics";
import { apiClient } from "../../src/api/client";

// Mock the API client
vi.mock("../../src/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
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

describe("Lyrics API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("lyricsKeys", () => {
    it("should generate correct all key", () => {
      expect(lyricsKeys.all).toEqual(["lyrics"]);
    });

    it("should generate correct song key", () => {
      expect(lyricsKeys.song("song-123")).toEqual([
        "lyrics",
        "song",
        "song-123",
      ]);
    });

    it("should generate correct search key", () => {
      expect(lyricsKeys.search("Test Song", "Test Artist")).toEqual([
        "lyrics",
        "search",
        "Test Song",
        "Test Artist",
      ]);
    });
  });

  describe("getLyricsForSong", () => {
    const mockLyricsResponse: LyricsResponse = {
      entity_id: "song-123",
      lyrics_text: "These are the lyrics",
      lyrics_synced: null,
      source: "genius",
      from_cache: false,
    };

    it("should fetch lyrics for a song", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockLyricsResponse });

      const result = await getLyricsForSong("song-123");

      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/lyrics/entity/song-123",
        { params: undefined }
      );
      expect(result).toEqual(mockLyricsResponse);
    });

    it("should fetch lyrics with force refresh", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockLyricsResponse });

      await getLyricsForSong("song-123", true);

      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/lyrics/entity/song-123",
        { params: { force_refresh: true } }
      );
    });

    it("should return not found response when lyrics not available", async () => {
      const notFoundResponse: LyricsNotFoundResponse = {
        entity_id: "song-123",
        message: "Lyrics not found",
      };
      mockApiClient.get.mockResolvedValueOnce({ data: notFoundResponse });

      const result = await getLyricsForSong("song-123");

      expect(result).toEqual(notFoundResponse);
    });

    it("should return fallback on API failure instead of throwing", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Network error"));

      const result = await getLyricsForSong("song-123");

      expect(result).toEqual({
        entity_id: "song-123",
        message: "Failed to fetch lyrics",
      });
    });
  });

  describe("searchLyrics", () => {
    const mockLyricsResponse: LyricsResponse = {
      entity_id: "song-123",
      lyrics_text: "Found lyrics",
      lyrics_synced: null,
      source: "musixmatch",
      from_cache: false,
    };

    it("should search for lyrics by name and artist", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockLyricsResponse });

      const result = await searchLyrics("Test Song", "Test Artist");

      expect(mockApiClient.get).toHaveBeenCalledWith("/lyrics/search", {
        params: { name: "Test Song", artist: "Test Artist" },
      });
      expect(result).toEqual(mockLyricsResponse);
    });

    it("should return fallback on API failure instead of throwing", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Search failed"));

      const result = await searchLyrics("Song", "Artist");

      expect(result).toEqual({
        entity_id: "Artist:Song",
        message: "Lyrics search failed",
      });
    });
  });

  describe("useLyrics hook", () => {
    const mockLyricsResponse: LyricsResponse = {
      entity_id: "song-123",
      lyrics_text: "Hook lyrics",
      lyrics_synced: null,
      source: "genius",
      from_cache: true,
    };

    it("should fetch lyrics when song ID is provided", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockLyricsResponse });

      const { result } = renderHook(() => useLyrics("song-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockLyricsResponse);
    });

    it("should not fetch when song ID is undefined", async () => {
      const { result } = renderHook(() => useLyrics(undefined), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it("should not fetch when enabled is false", async () => {
      const { result } = renderHook(
        () => useLyrics("song-123", { enabled: false }),
        {
          wrapper: createWrapper(),
        }
      );

      expect(result.current.fetchStatus).toBe("idle");
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it("should succeed with fallback on API error (catch returns value)", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Fetch failed"));

      const { result } = renderHook(() => useLyrics("song-123"), {
        wrapper: createWrapper(),
      });

      // getLyricsForSong catches errors and returns a fallback, so the query succeeds
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual({
        entity_id: "song-123",
        message: "Failed to fetch lyrics",
      });
    });
  });

  describe("useRefreshLyrics hook", () => {
    const mockLyricsResponse: LyricsResponse = {
      entity_id: "song-123",
      lyrics_text: "Refreshed lyrics",
      lyrics_synced: "[00:00.00] Synced",
      source: "genius",
      from_cache: false,
    };

    it("should refresh lyrics with force flag", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockLyricsResponse });

      const { result } = renderHook(() => useRefreshLyrics(), {
        wrapper: createWrapper(),
      });

      result.current.mutate("song-123");

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/lyrics/entity/song-123",
        { params: { force_refresh: true } }
      );
    });

    it("should succeed with fallback on error (catch returns value)", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Refresh failed"));

      const { result } = renderHook(() => useRefreshLyrics(), {
        wrapper: createWrapper(),
      });

      result.current.mutate("song-123");

      // getLyricsForSong catches and returns fallback, so mutation succeeds
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("useSearchLyrics hook", () => {
    const mockLyricsResponse: LyricsResponse = {
      entity_id: "search-result",
      lyrics_text: "Search result lyrics",
      lyrics_synced: null,
      source: "azlyrics",
      from_cache: false,
    };

    it("should search for lyrics", async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: mockLyricsResponse });

      const { result } = renderHook(() => useSearchLyrics(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ name: "Test Song", artist: "Test Artist" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockApiClient.get).toHaveBeenCalledWith("/lyrics/search", {
        params: { name: "Test Song", artist: "Test Artist" },
      });
      expect(result.current.data).toEqual(mockLyricsResponse);
    });

    it("should succeed with fallback on error (catch returns value)", async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error("Search failed"));

      const { result } = renderHook(() => useSearchLyrics(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ name: "Unknown", artist: "Unknown" });

      // searchLyrics catches and returns fallback, so mutation succeeds
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("hasLyrics helper", () => {
    it("should return true for response with lyrics", () => {
      const response: LyricsResponse = {
        entity_id: "song-123",
        lyrics_text: "Some lyrics",
        lyrics_synced: null,
        source: "genius",
        from_cache: false,
      };

      expect(hasLyrics(response)).toBe(true);
    });

    it("should return false for not found response", () => {
      const response: LyricsNotFoundResponse = {
        entity_id: "song-123",
        message: "Not found",
      };

      expect(hasLyrics(response)).toBe(false);
    });

    it("should return false for response with empty lyrics", () => {
      const response = {
        entity_id: "song-123",
        lyrics_text: "",
        lyrics_synced: null,
        source: "genius",
        from_cache: false,
      } as LyricsResponse;

      expect(hasLyrics(response)).toBe(false);
    });
  });

  describe("toLyrics helper", () => {
    it("should convert API response to Lyrics type", () => {
      const response: LyricsResponse = {
        entity_id: "song-123",
        lyrics_text: "Test lyrics",
        lyrics_synced: "[00:00.00] Synced",
        source: "genius",
        from_cache: false,
      };

      const result = toLyrics(response);

      expect(result.entity_id).toBe("song-123");
      expect(result.lyrics_text).toBe("Test lyrics");
      expect(result.lyrics_synced).toBe("[00:00.00] Synced");
      expect(result.source).toBe("genius");
      expect(result.fetched_at).toBeDefined();
    });

    it("should handle null synced lyrics", () => {
      const response: LyricsResponse = {
        entity_id: "song-123",
        lyrics_text: "Test lyrics",
        lyrics_synced: null,
        source: "musixmatch",
        from_cache: false,
      };

      const result = toLyrics(response);

      expect(result.lyrics_synced).toBeNull();
    });
  });
});
