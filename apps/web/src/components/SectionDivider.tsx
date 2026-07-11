import type { ReactNode } from "react";
import { cn } from "../lib/utils";

// A section header on a single divider line (Layout v2): an eyebrow label, an
// optional mono count, and optional right-aligned actions. Used to head the
// entity pages' Top tracks / Discography / Tracks sections and the settings
// sections. The `accent` prop is retained for API compatibility; the Control
// Room system uses one amber operator accent + emerald community voice, so the
// divider itself stays neutral.
type Accent = "emerald" | "gold" | "teal" | "deezer";

export function SectionDivider({
  title,
  count,
  action,
  accent: _accent = "emerald",
  icon,
  className,
}: {
  title: string;
  count?: number;
  /** Right-aligned controls on the divider line (filters, buttons). */
  action?: ReactNode;
  accent?: Accent;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 border-b border-border pb-2",
        className,
      )}
    >
      {icon ? <span className="text-faint">{icon}</span> : null}
      <h2 className="text-xs font-medium uppercase tracking-wider text-faint">
        {title}
      </h2>
      {count !== undefined ? (
        <span className="font-mono text-xs text-faint tnum">{count}</span>
      ) : null}
      {action ? <div className="ml-auto flex items-center gap-2">{action}</div> : null}
    </div>
  );
}
