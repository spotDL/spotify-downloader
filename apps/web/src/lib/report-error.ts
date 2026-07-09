import { isApiError } from "../api/errors";
import { toast } from "../components/Toasts";

/**
 * Toast a thrown mutation error. Every non-2xx is normalized to an `ApiError` by
 * the client's error interceptor (CONTRACT C/F) before it reaches an `onError`
 * handler, so a typed error maps to its CONTRACT F copy; anything else (a bug, a
 * thrown non-error) degrades to the caller's fallback message.
 */
export function reportError(err: unknown, fallback: string): void {
  if (isApiError(err)) toast.fromApiError(err);
  else toast.error(fallback);
}
