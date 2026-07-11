import { toast as sonnerToast } from "sonner";
import {
  type ApiError,
  type Severity,
  messageForApiError,
  severityForApiError,
} from "../api/errors";

// Imperative toast API — callable from anywhere (mutation `onError` handlers,
// route guards, the ws hook). This is a thin shim over sonner; the visible
// <Toaster/> is mounted once at the app root (see components/ui/sonner). The
// exported surface (`toast`, `useToast`, `Toasts`) is preserved so existing
// call sites keep working.

function emit(message: string, severity: Severity) {
  if (severity === "error") return sonnerToast.error(message);
  if (severity === "warn") return sonnerToast.warning(message);
  return sonnerToast.info(message);
}

export const toast = {
  push: (message: string, severity: Severity = "info") => emit(message, severity),
  info: (message: string) => sonnerToast.info(message),
  warn: (message: string) => sonnerToast.warning(message),
  error: (message: string) => sonnerToast.error(message),
  /** Map an ApiError to its CONTRACT F copy + severity and raise it. */
  fromApiError: (e: ApiError) => emit(messageForApiError(e), severityForApiError(e)),
  dismiss: (id?: string | number) => sonnerToast.dismiss(id),
  /** Drop every visible toast (used to reset between tests). */
  clear: () => sonnerToast.dismiss(),
};

export function useToast() {
  return { toast };
}

/**
 * Legacy mount point. The Control Room toaster now mounts at the app root via
 * `components/ui/sonner`'s <Toaster/>, so this renders nothing.
 */
export function Toasts() {
  return null;
}
