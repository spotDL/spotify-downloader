import type { ReactNode } from "react";
import { cn } from "../lib/utils";
import { Card as UICard } from "./ui/card";

// The panel primitive: a flat token surface with an optional header (title + a
// mono "more" note). Shared by the detail pages' match/lyrics/listen-on/details
// panels. `glass` is retained for API compatibility but is now a flat card.
export function Card({
  title,
  action,
  glass: _glass = false,
  className,
  children,
}: {
  title?: string;
  action?: ReactNode;
  glass?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <UICard className={cn("p-5", className)}>
      {title !== undefined || action !== undefined ? (
        <div className="mb-3.5 flex items-center justify-between gap-3">
          {title !== undefined ? (
            <h3 className="font-display text-sm font-semibold tracking-tight text-foreground">
              {title}
            </h3>
          ) : (
            <span />
          )}
          {action !== undefined ? (
            <span className="font-mono text-[11px] text-muted-foreground tnum">{action}</span>
          ) : null}
        </div>
      ) : null}
      {children}
    </UICard>
  );
}

// A key/value detail row: dim label, mono tabular value.
export function DetailRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-1.5 text-[12.5px] last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tnum text-foreground">{children}</span>
    </div>
  );
}
