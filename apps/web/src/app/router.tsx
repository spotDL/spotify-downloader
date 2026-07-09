import { createRouter } from "@tanstack/react-router";
import type { QueryClient } from "@tanstack/react-query";
import { routeTree } from "../routeTree.gen";
import type { ConfigResponse } from "../api/generated/types.gen";
import { useAuthStore } from "../stores/auth";
import { queryClient } from "./query-client";

// The router context (CONTRACT G): `config` is injected by ConfigGate via the
// RouterProvider `context` prop once GET /config resolves, so `beforeLoad`
// guards (Task 4) read the mode/flags and auth state synchronously.
export interface RouterAuthContext {
  getAccessToken(): string | null;
}

export interface RouterContext {
  queryClient: QueryClient;
  config: ConfigResponse;
  auth: RouterAuthContext;
}

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  context: {
    queryClient,
    auth: { getAccessToken: () => useAuthStore.getState().accessToken },
    // Overwritten by ConfigGate before render; the placeholder satisfies the
    // context type at router-creation time.
    config: undefined as unknown as ConfigResponse,
  },
  scrollRestoration: true,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
