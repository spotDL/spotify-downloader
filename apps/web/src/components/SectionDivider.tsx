import type { ReactNode } from "react";

// A section heading with a colour-tinted accent bar + icon and an optional
// count. Used to divide search sections (Artists / Albums / Songs / Playlists)
// and the artist page's Top tracks / Discography (mockup `.section-title`).

type Accent = "emerald" | "gold" | "teal" | "deezer";

const BAR: Record<Accent, string> = {
  emerald: "bg-emerald",
  gold: "bg-gold",
  teal: "bg-teal",
  deezer: "bg-deezer",
};
const ICON: Record<Accent, string> = {
  emerald: "text-emerald",
  gold: "text-gold",
  teal: "text-teal",
  deezer: "text-deezer",
};

export function SectionDivider({
  title,
  count,
  accent = "emerald",
  icon,
  className = "",
}: {
  title: string;
  count?: number;
  accent?: Accent;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <span className={`h-4 w-1 rounded-full ${BAR[accent]}`} aria-hidden />
      {icon ? <span className={`${ICON[accent]}`}>{icon}</span> : null}
      <h2 className="text-[15px] font-bold tracking-tight text-fg">{title}</h2>
      {count !== undefined ? (
        <span className="font-mono text-xs text-muted tabular-nums">{count}</span>
      ) : null}
    </div>
  );
}
