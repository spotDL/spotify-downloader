import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Song, Match } from "@/types";

export type DownloadStatus =
  | "pending"
  | "searching"
  | "downloading"
  | "converting"
  | "embedding"
  | "completed"
  | "failed"
  | "cancelled";

export interface QueueItem {
  id: string;
  song: Song;
  match?: Match;
  status: DownloadStatus;
  progress: number;
  speed: string | null;
  eta: string | null;
  error: string | null;
  addedAt: string;
  completedAt: string | null;
}

interface QueueState {
  items: QueueItem[];
  maxConcurrent: number;

  // Actions
  addItem: (song: Song, match?: Match) => string;
  removeItem: (id: string) => void;
  updateItem: (id: string, updates: Partial<QueueItem>) => void;
  clearCompleted: () => void;
  clearFailed: () => void;
  clearAll: () => void;
  retryFailed: (id: string) => void;
  setMaxConcurrent: (max: number) => void;

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

      addItem: (song, match) => {
        const id = crypto.randomUUID();
        const item: QueueItem = {
          id,
          song,
          match: match ?? undefined,
          status: "pending",
          progress: 0,
          speed: null,
          eta: null,
          error: null,
          addedAt: new Date().toISOString(),
          completedAt: null,
        };
        set((state) => ({ items: [...state.items, item] }));
        return id;
      },

      removeItem: (id) => {
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
        set((state) => ({
          items: state.items.filter((item) => item.status !== "completed"),
        }));
      },

      clearFailed: () => {
        set((state) => ({
          items: state.items.filter((item) => item.status !== "failed"),
        }));
      },

      clearAll: () => {
        set({ items: [] });
      },

      retryFailed: (id) => {
        set((state) => ({
          items: state.items.map((item) =>
            item.id === id && item.status === "failed"
              ? { ...item, status: "pending" as const, error: null, progress: 0 }
              : item
          ),
        }));
      },

      setMaxConcurrent: (max) => {
        set({ maxConcurrent: max });
      },

      getPendingCount: () =>
        get().items.filter((item) => item.status === "pending").length,

      getActiveCount: () =>
        get().items.filter((item) =>
          ["searching", "downloading", "converting", "embedding"].includes(
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
          (item) => item.status !== "downloading" && item.status !== "searching"
        ),
        maxConcurrent: state.maxConcurrent,
      }),
    }
  )
);
