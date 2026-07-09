import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "../api/errors";

// The single app QueryClient (a module singleton so `app/router.tsx` and
// `main.tsx` share one instance — it lives in the router context and is what the
// WS hook and mutation invalidations write through).
//
// Retry policy (CONTRACT): a 4xx `ApiError` is a deterministic client/rule error
// (not_found, validation_error, forbidden, …) — retrying can't help, so never
// retry it. Everything else gets a small bounded retry for transient blips.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (isApiError(error) && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});
