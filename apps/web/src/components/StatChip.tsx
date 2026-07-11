import type { ReactNode } from "react";
import { cn } from "../lib/utils";

// A mono, tabular-nums stat chip: a dim label ("dur", "album", "year") beside a
// bright value. The atomic unit of the hero stat rows.
export function StatChip({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1.5 font-mono text-xs tnum text-foreground",
        className,
      )}
    >
      <span className="text-[11px] text-muted-foreground">{label}</span>
      {children}
    </span>
  );
}
