import { useEffect, useRef, useState } from "react";
import { create } from "zustand";
import {
  type ApiError,
  type Severity,
  messageForApiError,
  severityForApiError,
} from "../api/errors";

// The toast queue is a module-level store (no provider needed), so `toast.*`
// can be called from mutation `onError` handlers, route guards, or anywhere.
// The <Toasts/> viewport (mounted once in the AppShell) renders it.
// CONTRACT H: severity → color/icon; auto-dismiss with pause-on-hover; the
// viewport is aria-live="polite". Task 5 finalizes the visual treatment.

export type ToastItem = {
  id: string;
  message: string;
  severity: Severity;
};

type ToastStore = {
  toasts: ToastItem[];
  push: (message: string, severity: Severity) => string;
  dismiss: (id: string) => void;
};

let counter = 0;
const nextId = () => `toast-${(counter += 1)}`;

const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  push: (message, severity) => {
    const id = nextId();
    set((state) => ({ toasts: [...state.toasts, { id, message, severity }] }));
    return id;
  },
  dismiss: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

/** Imperative toast API — callable from anywhere (CONTRACT F/H). */
export const toast = {
  push: (message: string, severity: Severity = "info") =>
    useToastStore.getState().push(message, severity),
  info: (message: string) => useToastStore.getState().push(message, "info"),
  warn: (message: string) => useToastStore.getState().push(message, "warn"),
  error: (message: string) => useToastStore.getState().push(message, "error"),
  /** Map an ApiError to its CONTRACT F copy + severity and enqueue it. */
  fromApiError: (e: ApiError) =>
    useToastStore
      .getState()
      .push(messageForApiError(e), severityForApiError(e)),
  dismiss: (id: string) => useToastStore.getState().dismiss(id),
};

export function useToast() {
  const toasts = useToastStore((state) => state.toasts);
  return { toasts, toast };
}

const SEVERITY_STYLES: Record<Severity, string> = {
  error: "border-danger/40 bg-danger/10 text-danger",
  warn: "border-warn/40 bg-warn/10 text-fg",
  info: "border-brand-500/40 bg-brand-50 text-fg dark:bg-brand-700/20",
};

const AUTO_DISMISS_MS = 6000;

function ToastRow({ item }: { item: ToastItem }) {
  const dismiss = useToastStore((state) => state.dismiss);
  const [paused, setPaused] = useState(false);
  const dismissRef = useRef(dismiss);
  dismissRef.current = dismiss;

  useEffect(() => {
    if (paused) return;
    const handle = setTimeout(() => dismissRef.current(item.id), AUTO_DISMISS_MS);
    return () => clearTimeout(handle);
  }, [paused, item.id]);

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-card border px-4 py-3 text-sm shadow-card ${SEVERITY_STYLES[item.severity]}`}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <span className="flex-1">{item.message}</span>
      <button
        type="button"
        aria-label="Dismiss notification"
        className="text-muted hover:text-fg"
        onClick={() => dismiss(item.id)}
      >
        ×
      </button>
    </div>
  );
}

/** Toast viewport — mount once in the AppShell. */
export function Toasts() {
  const toasts = useToastStore((state) => state.toasts);
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end"
    >
      {toasts.map((item) => (
        <ToastRow key={item.id} item={item} />
      ))}
    </div>
  );
}
