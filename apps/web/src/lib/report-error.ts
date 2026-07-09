import { ApiError, isApiError } from "../api/errors";
import type { ErrorCode } from "../api/generated/types.gen";
import { toast } from "../components/Toasts";

// Normalize a thrown mutation error to a toast. Post-integration the client
// interceptor (CONTRACT C) hands us an `ApiError`; until then the generated
// client throws the raw `ErrorEnvelope` body. Both carry a stable `code`, so we
// surface the CONTRACT F copy either way and fall back to a generic message.
function asApiError(err: unknown): ApiError | null {
  if (isApiError(err)) return err;
  if (err && typeof err === "object" && "code" in err) {
    const envelope = err as {
      code: unknown;
      message?: unknown;
      detail?: unknown;
    };
    if (typeof envelope.code === "string") {
      const message =
        typeof envelope.message === "string" ? envelope.message : "";
      const detail =
        envelope.detail && typeof envelope.detail === "object"
          ? (envelope.detail as Record<string, unknown>)
          : null;
      return new ApiError(envelope.code as ErrorCode, message, detail, 0);
    }
  }
  return null;
}

/** Toast a thrown mutation error (typed code → CONTRACT F copy, else fallback). */
export function reportError(err: unknown, fallback: string): void {
  const apiError = asApiError(err);
  if (apiError) toast.fromApiError(apiError);
  else toast.error(fallback);
}
