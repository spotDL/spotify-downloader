import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

// UI-only state (CONTRACT — stores hold NO server state).
type UiStore = {
  theme: Theme;
  navCollapsed: boolean;
  setTheme: (theme: Theme) => void;
  toggleNav: () => void;
};

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      theme: "system",
      navCollapsed: false,
      setTheme: (theme) => set({ theme }),
      toggleNav: () => set((state) => ({ navCollapsed: !state.navCollapsed })),
    }),
    { name: "spotdl-ui" },
  ),
);
