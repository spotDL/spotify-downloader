import type { ReactNode } from "react";

// A mono, tabular-nums stat chip: a dim label ("dur", "album", "year") beside a
// bright value. The atomic unit of the hero stat rows (mockup `.chip`).
export function StatChip({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-baseline gap-1.5 font-mono text-xs tabular-nums text-fg ${className}`}
    >
      <span className="text-[11px] text-muted">{label}</span>
      {children}
    </span>
  );
}
