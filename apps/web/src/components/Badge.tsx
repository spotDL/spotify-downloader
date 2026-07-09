import type { ReactNode } from "react";

type Tone = "neutral" | "brand" | "warn" | "danger" | "muted";

const TONES: Record<Tone, string> = {
  neutral: "bg-black/5 text-fg dark:bg-white/10",
  brand: "bg-brand-100 text-brand-700 dark:bg-brand-700/30 dark:text-brand-100",
  warn: "bg-warn/20 text-warn",
  danger: "bg-danger/15 text-danger",
  muted: "bg-black/5 text-muted dark:bg-white/10",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
