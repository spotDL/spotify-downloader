import { create } from "zustand";

// In-memory auth state (CONTRACT C) — NEVER persisted. The short-lived access
// token (15-min TTL) is an XSS-exposed value, so it lives only in memory and is
// re-minted from the persisted refresh token on boot (bootstrapAuth).
//
// NOTE: the authenticated user profile & `is_admin` come from the ["me"] QUERY
// (server state), never a field here.
type AuthStore = {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  reset: () => void;
};

export const useAuthStore = create<AuthStore>()((set) => ({
  accessToken: null,
  setAccessToken: (accessToken) => set({ accessToken }),
  reset: () => set({ accessToken: null }),
}));
