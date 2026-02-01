import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Song, Match, DisplayEntityType } from "@/types";
import {
  startDownload,
  getDownloadStatus,
  cancelDownload,
  getDownloadFileUrl,
  findMatches,
  type DownloadProgress,
} from "@/api";
import { useSettingsStore } from "./settings";

export type DownloadStatus =
  | "pending"
  | "searching"
  | "downloading"
  | "processing"
  | "converting"
  | "embedding"
  | "completed"
  | "failed"
  | "cancelled";

export interface EntityContext {
  type: DisplayEntityType;
  name: string;
  url: string;
  position: number;
  total: number;
}

export interface QueueItem {
  id: string;
  downloadId: string | null; // Backend download ID
  song: Song;
  match?: Match;
  status: DownloadStatus;
  progress: number;
  speed: string | null;
  eta: string | null;
  filename: string | null;
  error: string | null;
  addedAt: string;
  completedAt: string | null;
  entityContext?: EntityContext;
}

export interface BulkEntityInfo {
  type: DisplayEntityType;
  name: string;
  url: string;
}

interface QueueState {
  items: QueueItem[];
  pollingIntervals: Map<string, ReturnType<typeof setInterval>>;

  // Actions
  addItem: (song: Song, match?: Match, entityContext?: EntityContext) => string;
  addBulkItems: (songs: Song[], entity: BulkEntityInfo) => string[];
  removeItem: (id: string) => void;
  updateItem: (id: string, updates: Partial<QueueItem>) => void;
  clearCompleted: () => void;
  clearFailed: () => void;
  clearAll: () => void;
  retryFailed: (id: string) => void;

  // Download actions
  startDownload: (queueId: string) => Promise<void>;
  cancelDownload: (queueId: string) => Promise<void>;
  pollDownloadStatus: (queueId: string, downloadId: string) => void;
  stopPolling: (queueId: string) => void;
  processQueue: () => void;
  downloadFile: (queueId: string) => void;

  // Selectors
  getPendingCount: () => number;
  getActiveCount: () => number;
  getCompletedCount: () => number;
  getFailedCount: () => number;
  getEntityGroups: () => Map<string, QueueItem[]>;
}

export const useQueueStore = create<QueueState>()(
  persist(
    (set, get) => ({
      items: [],
      pollingIntervals: new Map(),

      addItem: (song, match, entityContext) => {
        const id = crypto.randomUUID();
        const item: QueueItem = {
          id,
          downloadId: null,
          song,
          match: match ?? undefined,
          status: "pending",
          progress: 0,
          speed: null,
          eta: null,
          filename: null,
          error: null,
          addedAt: new Date().toISOString(),
          completedAt: null,
          entityContext,
        };
        set((state) => ({ items: [...state.items, item] }));

        // Process queue after adding
        setTimeout(() => get().processQueue(), 0);

        return id;
      },

      addBulkItems: (songs, entity) => {
        const ids: string[] = [];
        const newItems: QueueItem[] = [];
        const total = songs.length;

        songs.forEach((song, index) => {
          const id = crypto.randomUUID();
          ids.push(id);

          const item: QueueItem = {
            id,
            downloadId: null,
            song,
            match: undefined,
            status: "pending",
            progress: 0,
            speed: null,
            eta: null,
            filename: null,
            error: null,
            addedAt: new Date().toISOString(),
            completedAt: null,
            entityContext: {
              type: entity.type,
              name: entity.name,
              url: entity.url,
              position: index + 1,
              total,
            },
          };
          newItems.push(item);
        });

        set((state) => ({ items: [...state.items, ...newItems] }));

        // Process queue after adding
        setTimeout(() => get().processQueue(), 0);

        return ids;
      },

      removeItem: (id) => {
        get().stopPolling(id);
        set((state) => ({
          items: state.items.filter((item) => item.id !== id),
        }));
      },

      updateItem: (id, updates) => {
        set((state) => ({
          items: state.items.map((item) =>
            item.id === id ? { ...item, ...updates } : item
          ),
        }));
      },

      clearCompleted: () => {
        const completed = get().items.filter((item) => item.status === "completed");
        completed.forEach((item) => get().stopPolling(item.id));
        set((state) => ({
          items: state.items.filter((item) => item.status !== "completed"),
        }));
      },

      clearFailed: () => {
        const failed = get().items.filter((item) => item.status === "failed");
        failed.forEach((item) => get().stopPolling(item.id));
        set((state) => ({
          items: state.items.filter((item) => item.status !== "failed"),
        }));
      },

      clearAll: () => {
        // Stop all polling
        get().items.forEach((item) => get().stopPolling(item.id));
        set({ items: [] });
      },

      retryFailed: (id) => {
        set((state) => ({
          items: state.items.map((item) =>
            item.id === id && item.status === "failed"
              ? { ...item, status: "pending" as const, error: null, progress: 0, downloadId: null }
              : item
          ),
        }));
        // Process queue to start the retry
        setTimeout(() => get().processQueue(), 0);
      },

      startDownload: async (queueId) => {
        const item = get().items.find((i) => i.id === queueId);
        if (!item) return;

        let targetUrl = item.match?.target_url;

        // If no match, find one first
        if (!targetUrl) {
          try {
            get().updateItem(queueId, { status: "searching", progress: 0 });

            // Find a YouTube match for the song
            const matchResponse = await findMatches(item.song.url, ["youtube", "youtube_music"]);

            if (matchResponse.matches.length > 0) {
              const bestMatch = matchResponse.matches[0];
              targetUrl = bestMatch.target_url;
              // Store the match on the item
              get().updateItem(queueId, { match: bestMatch });
            } else {
              throw new Error("No download source found for this song");
            }
          } catch (error) {
            get().updateItem(queueId, {
              status: "failed",
              error: error instanceof Error ? error.message : "Failed to find download source",
            });
            get().processQueue();
            return;
          }
        }

        try {
          get().updateItem(queueId, { status: "downloading", progress: 0 });

          // Get user's download preferences from settings
          const settings = useSettingsStore.getState();

          const response = await startDownload({
            url: targetUrl,
            title: item.song.name,
            artist: item.song.artists.join(", "),
            album: item.song.album_name ?? undefined,
            cover_url: item.song.cover_url ?? undefined,
            duration: item.song.duration,
            output_format: settings.audioFormat,
            quality: settings.audioQuality === "best" ? "320" : settings.audioQuality.replace("k", ""),
            embed_metadata: settings.embedMetadata,
            embed_lyrics: settings.embedLyrics,
            embed_cover_art: settings.embedCoverArt,
          });

          get().updateItem(queueId, { downloadId: response.download_id });
          get().pollDownloadStatus(queueId, response.download_id);
        } catch (error) {
          get().updateItem(queueId, {
            status: "failed",
            error: error instanceof Error ? error.message : "Failed to start download",
          });
          get().processQueue();
        }
      },

      cancelDownload: async (queueId) => {
        const item = get().items.find((i) => i.id === queueId);
        if (!item?.downloadId) return;

        try {
          await cancelDownload(item.downloadId);
          get().stopPolling(queueId);
          get().updateItem(queueId, { status: "cancelled" });
          get().processQueue();
        } catch {
          // Cancel failed - download will continue, which is visible in the UI
        }
      },

      pollDownloadStatus: (queueId, downloadId) => {
        // Clear existing interval
        get().stopPolling(queueId);

        const poll = async () => {
          try {
            const progress: DownloadProgress = await getDownloadStatus(downloadId);

            // Map backend status to frontend status
            let status: DownloadStatus = progress.status;
            if (progress.status === "processing") {
              status = "processing";
            }

            get().updateItem(queueId, {
              status,
              progress: progress.progress,
              speed: progress.speed,
              eta: progress.eta,
              filename: progress.filename,
              error: progress.error ?? null,
              completedAt: progress.completed_at ?? null,
            });

            // Stop polling if download is done
            if (["completed", "failed", "cancelled"].includes(progress.status)) {
              get().stopPolling(queueId);
              get().processQueue();

              // Auto-download the file if completed
              if (progress.status === "completed") {
                get().downloadFile(queueId);
              }
            }
          } catch {
            // Polling failed - will retry on next interval
          }
        };

        // Poll immediately, then every second
        poll();
        const interval = setInterval(poll, 1000);
        get().pollingIntervals.set(queueId, interval);
      },

      stopPolling: (queueId) => {
        const interval = get().pollingIntervals.get(queueId);
        if (interval) {
          clearInterval(interval);
          get().pollingIntervals.delete(queueId);
        }
      },

      processQueue: () => {
        const state = get();
        const activeCount = state.getActiveCount();
        const pendingItems = state.items.filter((item) => item.status === "pending");

        // Get max concurrent from settings store
        const maxConcurrent = useSettingsStore.getState().maxConcurrentDownloads;

        // Start downloads up to max concurrent
        const slotsAvailable = maxConcurrent - activeCount;
        const toStart = pendingItems.slice(0, slotsAvailable);

        toStart.forEach((item) => {
          state.startDownload(item.id);
        });
      },

      downloadFile: (queueId) => {
        const item = get().items.find((i) => i.id === queueId);
        if (!item?.downloadId) return;

        // Create a download link and trigger it
        const url = getDownloadFileUrl(item.downloadId);
        const link = document.createElement("a");
        link.href = url;
        link.download = item.filename || `${item.song.name} - ${item.song.artists.join(", ")}.mp3`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      },

      getPendingCount: () =>
        get().items.filter((item) => item.status === "pending").length,

      getActiveCount: () =>
        get().items.filter((item) =>
          ["searching", "downloading", "processing", "converting", "embedding"].includes(
            item.status
          )
        ).length,

      getCompletedCount: () =>
        get().items.filter((item) => item.status === "completed").length,

      getFailedCount: () =>
        get().items.filter((item) => item.status === "failed").length,

      getEntityGroups: () => {
        const groups = new Map<string, QueueItem[]>();

        get().items.forEach((item) => {
          if (item.entityContext) {
            const key = `${item.entityContext.type}:${item.entityContext.url}`;
            const existing = groups.get(key) || [];
            existing.push(item);
            groups.set(key, existing);
          } else {
            // Items without entity context go to a special "individual" group
            const existing = groups.get("individual") || [];
            existing.push(item);
            groups.set("individual", existing);
          }
        });

        return groups;
      },
    }),
    {
      name: "spotdl-queue",
      partialize: (state) => ({
        items: state.items.filter(
          (item) => !["downloading", "searching", "processing"].includes(item.status)
        ),
      }),
      onRehydrateStorage: () => (state) => {
        // Auto-process queue when store is rehydrated from localStorage
        if (state) {
          setTimeout(() => state.processQueue(), 100);
        }
      },
    }
  )
);
