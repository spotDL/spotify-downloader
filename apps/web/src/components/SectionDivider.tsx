import type { ReactNode } from "react";
import { cn } from "../lib/utils";

// A section heading with a phosphor-amber accent bar + icon and an optional
// count. Used to divide search sections (Artists / Albums / Songs / Playlists)
// and the artist page's Top tracks / Discography. The `accent` prop is retained
// for API compatibility; the Control Room system uses a single amber accent.
type Accent = "emerald" | "gold" | "teal" | "deezer";

export function SectionDivider({
  title,
  count,
  accent: _accent = "emerald",
  icon,
  className,
}: {
  title: string;
  count?: number;
  accent?: Accent;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span className="h-4 w-1 rounded-full bg-primary" aria-hidden />
      {icon ? <span className="text-primary">{icon}</span> : null}
      <h2 className="font-display text-[15px] font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      {count !== undefined ? (
        <span className="font-mono text-xs text-muted-foreground tnum">{count}</span>
      ) : null}
    </div>
  );
}
