import type { ReactNode } from "react";
import { Badge as UIBadge } from "./ui/badge";

type Tone = "neutral" | "brand" | "ok" | "warn" | "danger" | "muted";

// Legacy tone names map onto the ui Badge variants. `ok` is the emerald
// positive voice (enabled/connected/verified states); `brand` stays amber.
const TONE_VARIANT = {
  neutral: "default",
  brand: "premium",
  ok: "success",
  warn: "warning",
  danger: "error",
  muted: "muted",
} as const;

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <UIBadge variant={TONE_VARIANT[tone]} className={className}>
      {children}
    </UIBadge>
  );
}
