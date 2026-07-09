import {
  type QueryClient,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
// The generated TanStack Query mutation/query factories are the ONLY write/read
// surface (spec §3). Components consume these app hooks, never the generated SDK
// directly (import-boundary guard, Task 5).
import {
  loginApiV1AuthLoginPostMutation,
  meApiV1AuthMeGetQueryKey,
  registerApiV1AuthRegisterPostMutation,
} from "./generated/@tanstack/react-query.gen";
import { logoutApiV1AuthLogoutPost } from "./generated/sdk.gen";
import type { ErrorCode, TokenResponse } from "./generated/types.gen";
import {
  ApiError,
  ERROR_MESSAGES,
  type Severity,
  messageForApiError,
  severityForApiError,
} from "./errors";
import { useAuthStore } from "../stores/auth";
import { useSessionStore } from "../stores/session";

// CONTRACT D — the auth mutations (login/register/logout), the `me` query, and
// the OAuth-fragment consumer. The download/vote/report mutations of CONTRACT D
// are added by their owning tasks (6–10); this file owns the auth surface only.

/** The `["me"]` query key (CONTRACT D). Uses the generated key so it stays in
 * lockstep with `useMe`'s query below. */
export function meQueryKey() {
  return meApiV1AuthMeGetQueryKey();
}

/** Invalidate the authenticated-profile query so `is_admin`/identity refetch. */
export function invalidateMe(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: meQueryKey() });
}

function storeTokens(token: TokenResponse): void {
  useAuthStore.getState().setAccessToken(token.access_token);
  useSessionStore.getState().setRefreshToken(token.refresh_token);
}

/** `POST /auth/login` — store the token pair, then invalidate `["me"]`. */
export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    ...loginApiV1AuthLoginPostMutation(),
    onSuccess: (data) => {
      storeTokens(data);
      void invalidateMe(queryClient);
    },
  });
}

/** `POST /auth/register` — store the token pair, then invalidate `["me"]`. */
export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    ...registerApiV1AuthRegisterPostMutation(),
    onSuccess: (data) => {
      storeTokens(data);
      void invalidateMe(queryClient);
    },
  });
}

/**
 * `POST /auth/logout` — revoke the refresh-token family server-side, then clear
 * the session and drop the per-user server state from the cache (CONTRACT D). We
 * clear regardless of the server result (`onSettled`): even if the revoke call
 * fails, the local session must end.
 */
export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const refreshToken = useSessionStore.getState().refreshToken;
      if (refreshToken === null) return;
      // Best-effort server revoke; local session is cleared in onSettled even if
      // this fails, so a dead server can't strand the user signed-in.
      await logoutApiV1AuthLogoutPost({
        body: { refresh_token: refreshToken },
        throwOnError: false,
      });
    },
    onSettled: () => {
      useAuthStore.getState().reset();
      useSessionStore.getState().clearAuth();
      // Drop per-user server state. Keys are the generated operation ids; match
      // by the `_id` prefix so `me`/downloads/admin/reports all clear.
      queryClient.removeQueries({
        predicate: (query) => {
          const id = (query.queryKey[0] as { _id?: string } | undefined)?._id ?? "";
          return (
            id.startsWith("meApiV1AuthMe") ||
            id.startsWith("listDownloads") ||
            id.startsWith("getDownload") ||
            id.startsWith("getBatch") ||
            id.includes("Admin") ||
            id.includes("Reports")
          );
        },
      });
    },
  });
}

/**
 * Outcome of consuming the OAuth callback URL fragment (CONTRACT C). Success has
 * already stored the token pair as a side effect; the route handles fragment
 * stripping, `["me"]` invalidation, and navigation.
 */
export type OauthOutcome =
  | { kind: "success" }
  | { kind: "error"; code: string }
  | { kind: "invalid" };

/**
 * Parse the OAuth callback fragment and act on it (CONTRACT C). Reads ONLY the
 * fragment — query params are ignored, so tokens never travel where the server,
 * proxies, or `Referer` headers can see them. On success it stores the token
 * pair; the caller strips the fragment and navigates.
 */
export function consumeOauthFragment(hash: string): OauthOutcome {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  const params = new URLSearchParams(raw);
  const error = params.get("error");
  if (error !== null) return { kind: "error", code: error };

  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");
  if (accessToken !== null && refreshToken !== null) {
    storeTokens({
      access_token: accessToken,
      refresh_token: refreshToken,
    } as TokenResponse);
    return { kind: "success" };
  }
  return { kind: "invalid" };
}

/**
 * Toast copy + severity for an OAuth `#error=<code>` (CONTRACT C). A code inside
 * the CONTRACT F vocabulary reuses its mapped copy; anything else (e.g. the
 * server's pinned `oauth_state_mismatch`) falls back to `Sign-in failed (code).`.
 */
export function oauthErrorMessage(code: string): {
  message: string;
  severity: Severity;
} {
  if (code in ERROR_MESSAGES) {
    const error = new ApiError(code as ErrorCode, "", null, 401);
    return {
      message: messageForApiError(error),
      severity: severityForApiError(error),
    };
  }
  return { message: `Sign-in failed (${code}).`, severity: "error" };
}
