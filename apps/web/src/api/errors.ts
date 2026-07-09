import type { ErrorCode } from "./generated/types.gen";

// CONTRACT F — the error envelope → ApiError → toast surface.
//
// Every non-2xx is normalized to an `ApiError` by the client interceptor
// (CONTRACT C, Task 4) before it reaches a query/mutation `onError`, so handlers
// get typed errors, never raw `Response`s.

export type Severity = "error" | "warn" | "info";

export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly detail: Record<string, unknown> | null;
  readonly status: number;

  constructor(
    code: ErrorCode,
    message: string,
    detail: Record<string, unknown> | null,
    status: number,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.detail = detail;
    this.status = status;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

function detailString(e: ApiError, key: string): string | undefined {
  const value = e.detail?.[key];
  return typeof value === "string" ? value : undefined;
}

function detailNumber(e: ApiError, key: string): number | undefined {
  const value = e.detail?.[key];
  return typeof value === "number" ? value : undefined;
}

// The full CONTRACT F table. Typed as `Record<ErrorCode, ...>` so a regenerated
// client that adds a code fails compilation here until a message is added.
export const ERROR_MESSAGES: Record<ErrorCode, (e: ApiError) => string> = {
  not_found: () => "Not found.",
  no_match_found: () =>
    "No matching audio found — try searching, or submit a match URL.",
  unsupported_url: () => "That link or query isn't supported.",
  unsupported_entity: () =>
    "You can only download tracks, albums, or playlists.",
  not_an_audio_target: () => "That URL isn't a downloadable audio source.",
  validation_error: (e) => `Please check your input: ${e.message}`,
  rate_limited: (e) => {
    const retryAfter = detailNumber(e, "retry_after");
    return retryAfter === undefined
      ? "You're going a bit fast — try again shortly."
      : `You're going a bit fast — retry in ${retryAfter}s.`;
  },
  provider_unavailable: () =>
    "A metadata source is down; results may be thinner. Try again shortly.",
  provider_auth_error: () =>
    "The server's provider credentials were rejected — contact the operator.",
  downloads_disabled: () => "Downloads are disabled on this server.",
  download_failed: (e) => {
    const step = detailString(e, "step");
    return step ? `Download failed at ${step}.` : "Download failed.";
  },
  internal_error: () => "Something went wrong on the server.",
  authentication_required: () => "Please sign in to do that.",
  forbidden: () => "You don't have permission to do that.",
  invalid_token: () => "Your session expired — please sign in again.",
  token_expired: () => "Your session expired — please sign in again.",
  invalid_credentials: () => "Wrong email or password.",
  email_taken: () =>
    "An account with that email already exists — sign in instead.",
  oauth_email_required: () =>
    "Your OAuth account has no visible email; make one public or register with email + password.",
};

// Severity drives the toast color/icon (CONTRACT F / CONTRACT H).
export const ERROR_SEVERITY: Record<ErrorCode, Severity> = {
  not_found: "error",
  no_match_found: "warn",
  unsupported_url: "error",
  unsupported_entity: "warn",
  not_an_audio_target: "warn",
  validation_error: "warn",
  rate_limited: "warn",
  provider_unavailable: "warn",
  provider_auth_error: "error",
  downloads_disabled: "info",
  download_failed: "error",
  internal_error: "error",
  authentication_required: "info",
  forbidden: "error",
  invalid_token: "info",
  token_expired: "info",
  invalid_credentials: "error",
  email_taken: "warn",
  oauth_email_required: "warn",
};

/**
 * Render an ApiError to its user-facing toast copy. An unknown/future code
 * (a server ahead of the app) degrades gracefully to a generic message.
 */
export function messageForApiError(e: ApiError): string {
  const render = ERROR_MESSAGES[e.code];
  return render
    ? render(e)
    : `Server error (${e.code}): ${e.message}`;
}

export function severityForApiError(e: ApiError): Severity {
  return ERROR_SEVERITY[e.code] ?? "error";
}
