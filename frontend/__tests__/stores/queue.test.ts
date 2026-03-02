import { describe, it, expect, beforeEach } from "vitest";
import { useQueueStore } from "../../src/stores/queue";
import type { Song } from "../../src/types";

const mockSong: Song = {
  id: "test-song-1",
  platform: "spotify",
  platform_id: "abc123",
  url: "https://open.spotify.com/track/abc123",
  name: "Test Song",
  artists: ["Test Artist"],
  artist: "Test Artist",
  album_name: "Test Album",
  duration: 180,
  isrc: "USRC12345678",
};

const mockSong2: Song = {
  id: "test-song-2",
  platform: "deezer",
  platform_id: "def456",
  url: "https://www.deezer.com/track/def456",
  name: "Another Song",
  artists: ["Another Artist", "Featured Artist"],
  artist: "Another Artist",
  album_name: "Another Album",
  duration: 240,
  isrc: null,
};

describe("useQueueStore", () => {
  beforeEach(() => {
    // Clear queue before each test
    useQueueStore.getState().clearAll();
  });

  it("should start with empty queue", () => {
    const state = useQueueStore.getState();
    expect(state.items).toHaveLength(0);
    expect(state.getPendingCount()).toBe(0);
  });

  it("should add item to queue", () => {
    const id = useQueueStore.getState().addItem(mockSong);

    const state = useQueueStore.getState();
    expect(state.items).toHaveLength(1);
    expect(state.items[0].id).toBe(id);
    expect(state.items[0].song).toEqual(mockSong);
    expect(state.items[0].status).toBe("pending");
    expect(state.items[0].progress).toBe(0);
  });

  it("should add multiple items", () => {
    useQueueStore.getState().addItem(mockSong);
    useQueueStore.getState().addItem(mockSong2);

    expect(useQueueStore.getState().items).toHaveLength(2);
    expect(useQueueStore.getState().getPendingCount()).toBe(2);
  });

  it("should remove item from queue", () => {
    const id = useQueueStore.getState().addItem(mockSong);
    useQueueStore.getState().removeItem(id);

    expect(useQueueStore.getState().items).toHaveLength(0);
  });

  it("should update item status", () => {
    const id = useQueueStore.getState().addItem(mockSong);

    useQueueStore.getState().updateItem(id, {
      status: "downloading",
      progress: 50,
    });

    const item = useQueueStore.getState().items[0];
    expect(item.status).toBe("downloading");
    expect(item.progress).toBe(50);
  });

  it("should track active count", () => {
    const id1 = useQueueStore.getState().addItem(mockSong);
    const id2 = useQueueStore.getState().addItem(mockSong2);

    useQueueStore.getState().updateItem(id1, { status: "downloading" });

    expect(useQueueStore.getState().getPendingCount()).toBe(1);
    expect(useQueueStore.getState().getActiveCount()).toBe(1);
  });

  it("should track completed count", () => {
    const id = useQueueStore.getState().addItem(mockSong);

    useQueueStore.getState().updateItem(id, { status: "completed" });

    expect(useQueueStore.getState().getCompletedCount()).toBe(1);
    expect(useQueueStore.getState().getPendingCount()).toBe(0);
  });

  it("should track failed count", () => {
    const id = useQueueStore.getState().addItem(mockSong);

    useQueueStore.getState().updateItem(id, {
      status: "failed",
      error: "Download failed",
    });

    expect(useQueueStore.getState().getFailedCount()).toBe(1);
    expect(useQueueStore.getState().items[0].error).toBe("Download failed");
  });

  it("should clear completed items", () => {
    const id1 = useQueueStore.getState().addItem(mockSong);
    const id2 = useQueueStore.getState().addItem(mockSong2);

    useQueueStore.getState().updateItem(id1, { status: "completed" });

    useQueueStore.getState().clearCompleted();

    expect(useQueueStore.getState().items).toHaveLength(1);
    expect(useQueueStore.getState().items[0].id).toBe(id2);
  });

  it("should clear failed items", () => {
    const id1 = useQueueStore.getState().addItem(mockSong);
    const id2 = useQueueStore.getState().addItem(mockSong2);

    useQueueStore.getState().updateItem(id1, { status: "failed" });

    useQueueStore.getState().clearFailed();

    expect(useQueueStore.getState().items).toHaveLength(1);
    expect(useQueueStore.getState().items[0].id).toBe(id2);
  });

  it("should retry failed item", () => {
    const id = useQueueStore.getState().addItem(mockSong);

    useQueueStore.getState().updateItem(id, {
      status: "failed",
      error: "Network error",
      progress: 30,
    });

    useQueueStore.getState().retryFailed(id);

    const item = useQueueStore.getState().items[0];
    expect(item.status).toBe("pending");
    expect(item.error).toBeNull();
    expect(item.progress).toBe(0);
  });

  it("should clear all items", () => {
    useQueueStore.getState().addItem(mockSong);
    useQueueStore.getState().addItem(mockSong2);

    useQueueStore.getState().clearAll();

    expect(useQueueStore.getState().items).toHaveLength(0);
  });
});
