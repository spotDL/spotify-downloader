// Hand-written client-fetch runtime configuration (CONTRACT B / CONTRACT C).
//
// This module is imported by the GENERATED client (`generated/client.gen.ts`)
// via `openapi-ts.config.ts`'s `runtimeConfigPath`, so it must have no import
// cycle back into the generated SDK. It exports:
//   - `resolveHttpBase()` / `resolveWsBase()` — the runtime API-base-URL
//     resolution (one build → any self-hosted server, spec §8).
//   - `createClientConfig` — hey-api's runtime config hook; sets the initial
//     `baseUrl` to `resolveHttpBase() + "/api/v1"`.
//
// The refresh-once auth interceptors (CONTRACT C) and the per-request baseUrl
// re-read (Task 4) live here. This module is imported by the GENERATED client at
// module-eval time, so it must NOT reference the generated `client` instance at
// eval time (that would be a TDZ cycle). Instead `installAuthInterceptors(client)`
// is called once at boot (main.tsx / test setup) with the already-created client;
// it captures the instance and registers the interceptors.
// @hey-api/openapi-ts v0.99 bundles the client-fetch runtime into
// `generated/client/`, so the runtime-config + interceptor option types come
// from there (type-only imports — no runtime cycle).
import type {
  Client,
  CreateClientConfig,
  ResolvedRequestOptions,
} from "./generated/client";
import type {
  ErrorCode,
  ErrorEnvelope,
  RefreshApiV1AuthRefreshPostResponses,
  TokenResponse,
} from "./generated/types.gen";
import { useSessionStore } from "../stores/session";
import { useAuthStore } from "../stores/auth";
import { ApiError, isApiError } from "./errors";

/**
 * Resolve the HTTP origin the API lives at.
 *
 * Default (`apiBaseUrl === ""`) ⇒ `""` (same-origin — the SPA is served BY the
 * server it talks to). A non-empty override is normalized (trailing slashes
 * stripped) and points every request at that origin.
 */
export function resolveHttpBase(): string {
  const override = useSessionStore.getState().apiBaseUrl.trim();
  return override === "" ? "" : override.replace(/\/+$/, "");
}

/**
 * Resolve the WebSocket origin, mapped from the HTTP base:
 *   same-origin  ⇒ ws(s)://<location.host> per the page protocol
 *   http override ⇒ ws://…, https override ⇒ wss://…
 */
export function resolveWsBase(): string {
  const http = resolveHttpBase();
  if (http === "") {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${location.host}`;
  }
  return http.replace(/^http/, "ws");
}

// The client's `baseUrl` is the ORIGIN only. The server's exported openapi.json
// already carries the `/api/v1` prefix in every operation path (e.g.
// `/api/v1/config`), so the generated SDK urls include it — appending `/api/v1`
// here would double-prefix. Effective request URL = resolveHttpBase() +
// "/api/v1/<op>", i.e. same-origin `/api/v1/...` by default (CONTRACT B intent).
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: resolveHttpBase(),
});

// ---------------------------------------------------------------------------
// CONTRACT C — refresh-once auth interceptors
// ---------------------------------------------------------------------------

// Auth endpoints never carry a bearer (login/register mint a session; refresh
// authenticates with the opaque refresh token in its body, not the access JWT).
const REFRESH_PATH = "/api/v1/auth/refresh";
const AUTH_EXEMPT_PATHS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  REFRESH_PATH,
]);
// Envelope codes that mean "the access token is stale/missing" — the only ones
// that trigger a refresh-and-retry (CONTRACT C step 2).
const REFRESHABLE_CODES = new Set<ErrorCode>([
  "token_expired",
  "invalid_token",
  "authentication_required",
]);
// Marks a request as already-retried so a second 401 cannot loop (CONTRACT C).
const RETRY_HEADER = "x-spotdl-retried";

// The generated client instance, captured by installAuthInterceptors so the
// response interceptor + bootstrapAuth can issue the refresh call without an
// eval-time import cycle back into the generated SDK.
let apiClient: Client | null = null;
// Single-flight guard: concurrent 401s share ONE in-flight refresh (CONTRACT C).
let refreshPromise: Promise<boolean> | null = null;
let installed = false;

function clearSession(): void {
  useAuthStore.getState().reset();
  useSessionStore.getState().clearAuth();
}

function storeTokenPair(token: Pick<TokenResponse, "access_token" | "refresh_token">): void {
  useAuthStore.getState().setAccessToken(token.access_token);
  useSessionStore.getState().setRefreshToken(token.refresh_token);
}

/** Peek at a non-2xx body's `ErrorEnvelope.code` without consuming the response. */
async function peekErrorCode(response: Response): Promise<ErrorCode | null> {
  try {
    const body: unknown = await response.clone().json();
    const code = (body as { code?: unknown }).code;
    return typeof code === "string" ? (code as ErrorCode) : null;
  } catch {
    return null;
  }
}

/**
 * Rotate the refresh token (single-flight): the first caller kicks
 * `POST /auth/refresh`, all concurrent callers await the same promise. Resolves
 * `true` and stores the rotated pair on success, `false` on any failure.
 */
function ensureRefreshed(client: Client): Promise<boolean> {
  refreshPromise ??= doRefresh(client).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

async function doRefresh(client: Client): Promise<boolean> {
  const refreshToken = useSessionStore.getState().refreshToken;
  if (refreshToken === null) return false;
  // The client's own response interceptor short-circuits on REFRESH_PATH, so
  // this call cannot recurse into another refresh.
  const { data, error } = await client.post<RefreshApiV1AuthRefreshPostResponses>({
    url: REFRESH_PATH,
    body: { refresh_token: refreshToken },
  });
  if (error !== undefined || data === undefined) return false;
  storeTokenPair(data);
  return true;
}

/**
 * Request interceptor: re-read the API base URL per request (so a Settings
 * change takes effect without reload — the client's init `baseUrl` is fixed at
 * boot) and attach the bearer to everything except the auth endpoints.
 */
function authRequestInterceptor(request: Request): Request {
  const base = resolveHttpBase();
  const { pathname, search } = new URL(request.url);
  // Same-origin (`base === ""`) resolves against the current origin; an override
  // points every request at that origin. Rebuild only when the target differs.
  const desired = (base === "" ? location.origin : base) + pathname + search;
  let outgoing = request;
  if (desired !== request.url) {
    outgoing = new Request(desired, request);
  }
  const accessToken = useAuthStore.getState().accessToken;
  if (accessToken !== null && !AUTH_EXEMPT_PATHS.has(pathname)) {
    outgoing.headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return outgoing;
}

/**
 * Response interceptor (CONTRACT C step 2/3): on a refreshable 401, refresh once
 * (single-flight) and replay the original request exactly once. Hard-logs-out
 * when there is no refresh token, when the refresh fails, or when the replay
 * still 401s. The refresh endpoint itself is never refreshed (a 401 there means
 * the family was revoked — hard logout via the error path).
 */
function makeAuthResponseInterceptor(client: Client) {
  return async (
    response: Response,
    request: Request,
    options: ResolvedRequestOptions,
  ): Promise<Response> => {
    if (response.ok) return response;
    const { pathname } = new URL(request.url);
    if (pathname === REFRESH_PATH) return response;
    if (request.headers.get(RETRY_HEADER) !== null) return response;

    const code = await peekErrorCode(response);
    if (code === null || !REFRESHABLE_CODES.has(code)) return response;
    if (useSessionStore.getState().refreshToken === null) return response;

    const refreshed = await ensureRefreshed(client);
    if (!refreshed) {
      clearSession();
      return response;
    }

    // Replay the original request with the fresh bearer. Rebuild from the
    // resolved options (not by cloning `request`, whose body the first fetch
    // already consumed) so POST replays keep their serialized body.
    const accessToken = useAuthStore.getState().accessToken;
    const replay = new Request(request.url, {
      method: request.method,
      headers: new Headers(request.headers),
      body: options.serializedBody,
      redirect: "follow",
    });
    if (accessToken !== null) {
      replay.headers.set("Authorization", `Bearer ${accessToken}`);
    }
    replay.headers.set(RETRY_HEADER, "1");

    const doFetch = options.fetch ?? globalThis.fetch;
    const replayResponse = await doFetch(replay);
    if (replayResponse.status === 401) clearSession();
    return replayResponse;
  };
}

/**
 * Error interceptor (CONTRACT C step 4 / CONTRACT F): normalize every failure to
 * an `ApiError` so query/mutation `onError` handlers get typed errors, never a
 * raw `Response`, thrown envelope object, or network `TypeError`.
 */
function authErrorInterceptor(
  error: unknown,
  response: Response | undefined,
): ApiError {
  if (isApiError(error)) return error;
  const status = response?.status ?? 0;
  if (error !== null && typeof error === "object" && "code" in error) {
    const envelope = error as ErrorEnvelope;
    return new ApiError(
      envelope.code,
      envelope.message,
      envelope.detail ?? null,
      status,
    );
  }
  const message = typeof error === "string" && error !== "" ? error : "Request failed.";
  return new ApiError("internal_error", message, null, status);
}

/**
 * Register the CONTRACT C interceptors on the generated client. Idempotent (the
 * interceptors are only wired once) but always re-captures the client instance.
 * Called once at boot from main.tsx and from the test setup.
 */
export function installAuthInterceptors(client: Client): void {
  apiClient = client;
  if (installed) return;
  installed = true;
  client.interceptors.request.use(authRequestInterceptor);
  client.interceptors.response.use(makeAuthResponseInterceptor(client));
  client.interceptors.error.use(authErrorInterceptor);
}

/**
 * Boot-time auth bootstrap (CONTRACT C): if a refresh token exists but there is
 * no access token, mint one via `POST /auth/refresh` before authed UI renders.
 * A failed refresh clears the session (anonymous). No-op when interceptors have
 * not been installed yet (no client to talk to).
 */
export async function bootstrapAuth(): Promise<void> {
  const hasRefresh = useSessionStore.getState().refreshToken !== null;
  const hasAccess = useAuthStore.getState().accessToken !== null;
  if (!hasRefresh || hasAccess || apiClient === null) return;
  const refreshed = await ensureRefreshed(apiClient);
  if (!refreshed) clearSession();
}

/** Test-only hook: reset the single-flight guard between test cases. */
export function __resetAuthInterceptorState(): void {
  refreshPromise = null;
}
