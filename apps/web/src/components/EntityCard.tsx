import type { ReactNode } from "react";

// MERGE: replace with the design-system <EntityCard> (CONTRACT H / Plan 10
// Task 5, sibling track). This minimal placeholder is presentational only — a
// cover/leading slot, a title, an optional subtitle, and a trailing meta slot —
// so callers wrap it in a typed <Link> for navigation.
export function EntityCard({
  title,
  subtitle,
  meta,
  coverUrl,
  leading,
  className = "",
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  meta?: ReactNode;
  coverUrl?: string | null;
  leading?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center gap-3 rounded-card border border-black/10 bg-surface px-3 py-2 dark:border-white/10 ${className}`}
    >
      {coverUrl ? (
        <img
          src={coverUrl}
          alt=""
          className="size-12 shrink-0 rounded object-cover"
          loading="lazy"
        />
      ) : leading ? (
        <div className="flex size-12 shrink-0 items-center justify-center rounded bg-black/5 text-muted dark:bg-white/10">
          {leading}
        </div>
      ) : null}
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-fg">{title}</p>
        {subtitle ? <p className="truncate text-sm text-muted">{subtitle}</p> : null}
      </div>
      {meta != null ? (
        <div className="shrink-0 text-sm tabular-nums text-muted">{meta}</div>
      ) : null}
    </div>
  );
}
