import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

const RECENT_SEARCHES_MAX = 8;

// UI-only state (CONTRACT — stores hold NO server state). `recentSearches` is a
// local convenience history for the command palette / search screen, most-recent
// first and de-duplicated.
type UiStore = {
  theme: Theme;
  navCollapsed: boolean;
  recentSearches: string[];
  setTheme: (theme: Theme) => void;
  toggleNav: () => void;
  addRecentSearch: (query: string) => void;
  clearRecentSearches: () => void;
};

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      theme: "system",
      navCollapsed: false,
      recentSearches: [],
      setTheme: (theme) => set({ theme }),
      toggleNav: () => set((state) => ({ navCollapsed: !state.navCollapsed })),
      addRecentSearch: (query) =>
        set((state) => {
          const q = query.trim();
          if (q.length === 0) return state;
          const next = [q, ...state.recentSearches.filter((r) => r !== q)];
          return { recentSearches: next.slice(0, RECENT_SEARCHES_MAX) };
        }),
      clearRecentSearches: () => set({ recentSearches: [] }),
    }),
    { name: "spotdl-ui" },
  ),
);
