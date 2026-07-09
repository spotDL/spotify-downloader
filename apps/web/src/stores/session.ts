import { create } from "zustand";
import { persist } from "zustand/middleware";

// Session state (UI/session ONLY — CONTRACT: stores hold NO server state).
// Persisted to localStorage as "spotdl-session".
//   apiBaseUrl   — "" = same-origin; runtime override (CONTRACT B), e.g.
//                  "https://nas.local:7070" for a remote self-host.
//   refreshToken — the rotating opaque refresh token (CONTRACT C). The
//                  short-lived access token lives in the in-memory auth store,
//                  never here.
type SessionStore = {
  apiBaseUrl: string;
  refreshToken: string | null;
  setApiBaseUrl: (url: string) => void;
  setRefreshToken: (token: string | null) => void;
  clearAuth: () => void;
};

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      apiBaseUrl: "",
      refreshToken: null,
      setApiBaseUrl: (apiBaseUrl) => set({ apiBaseUrl }),
      setRefreshToken: (refreshToken) => set({ refreshToken }),
      // Clears the refresh token on logout / refresh failure but keeps the
      // configured apiBaseUrl (a server override outlives a session).
      clearAuth: () => set({ refreshToken: null }),
    }),
    { name: "spotdl-session" },
  ),
);
