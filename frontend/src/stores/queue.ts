import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Song, Match } from "@/types";
import {
  startDownload,
  getDownloadStatus,
  cancelDownload,
  getDownloadFileUrl,
  type DownloadProgress,
} from "@/api";

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
}

interface QueueState {
  items: QueueItem[];
  maxConcurrent: number;
  pollingIntervals: Map<string, ReturnType<typeof setInterval>>;

  // Actions
  addItem: (song: Song, match?: Match) => string;
  removeItem: (id: string) => void;
  updateItem: (id: string, updates: Partial<QueueItem>) => void;
  clearCompleted: () => void;
  clearFailed: () => void;
  clearAll: () => void;
  retryFailed: (id: string) => void;
  setMaxConcurrent: (max: number) => void;

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
}

export const useQueueStore = create<QueueState>()(
  persist(
    (set, get) => ({
      items: [],
      maxConcurrent: 3,
      pollingIntervals: new Map(),

      addItem: (song, match) => {
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
        };
        set((state) => ({ items: [...state.items, item] }));

        // Process queue after adding
        setTimeout(() => get().processQueue(), 0);

        return id;
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

      setMaxConcurrent: (max) => {
        set({ maxConcurrent: max });
        // Process queue in case more can start
        setTimeout(() => get().processQueue(), 0);
      },

      startDownload: async (queueId) => {
        const item = get().items.find((i) => i.id === queueId);
        if (!item || !item.match) return;

        try {
          get().updateItem(queueId, { status: "downloading", progress: 0 });

          const response = await startDownload({
            url: item.match.target_url,
            title: item.song.name,
            artist: item.song.artists.join(", "),
            album: item.song.album_name ?? undefined,
            cover_url: item.song.cover_url ?? undefined,
            duration: item.song.duration,
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
        } catch (error) {
          console.error("Failed to cancel download:", error);
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
          } catch (error) {
            console.error("Failed to poll download status:", error);
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

        // Start downloads up to max concurrent
        const slotsAvailable = state.maxConcurrent - activeCount;
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
    }),
    {
      name: "spotdl-queue",
      partialize: (state) => ({
        items: state.items.filter(
          (item) => !["downloading", "searching", "processing"].includes(item.status)
        ),
        maxConcurrent: state.maxConcurrent,
      }),
    }
  )
);
