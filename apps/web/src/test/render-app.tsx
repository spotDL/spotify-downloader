import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, createRouter } from "@tanstack/react-router";
import type { ConfigResponse } from "../api/generated/types.gen";
import { routeTree } from "../routeTree.gen";
import { ConfigGate } from "../app/config";
import { ThemeProvider } from "../app/theme";
import { useAuthStore } from "../stores/auth";

// Test harness that mounts the real app shell exactly as `main.tsx` composes it
// (QueryClient → Theme → ConfigGate → RouterProvider), but with a FRESH
// QueryClient + router per call so tests don't share cache/history. `/config`
// (and any other endpoint) is served by the MSW handlers, so the ConfigGate's
// boot fetch, bootstrapAuth seam, and gated nav all run for real.
export function renderApp(initialPath = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [initialPath] }),
    context: {
      queryClient,
      auth: { getAccessToken: () => useAuthStore.getState().accessToken },
      // ConfigGate injects the resolved config before render; this placeholder
      // only satisfies the context type at router-creation time.
      config: undefined as unknown as ConfigResponse,
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ConfigGate router={router} />
      </ThemeProvider>
    </QueryClientProvider>,
  );
}
