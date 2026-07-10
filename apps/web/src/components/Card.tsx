import type { ReactNode } from "react";

// The panel primitive (mockup `.card`): a surface tile with an optional header
// (title + a mono "more" note) and optional glassmorphism. Shared by the detail
// pages' match/lyrics/listen-on/details panels.
export function Card({
  title,
  action,
  glass = false,
  className = "",
  children,
}: {
  title?: string;
  action?: ReactNode;
  glass?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={`rounded-card border border-line-soft px-5 py-4 ${
        glass ? "glass" : "bg-surface"
      } ${className}`}
    >
      {title !== undefined || action !== undefined ? (
        <div className="mb-3.5 flex items-center justify-between gap-3">
          {title !== undefined ? (
            <h3 className="text-sm font-bold tracking-tight text-fg">{title}</h3>
          ) : (
            <span />
          )}
          {action !== undefined ? (
            <span className="font-mono text-[11px] text-muted">{action}</span>
          ) : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

// A key/value detail row (mockup `.kv`): dim label, mono tabular value.
export function DetailRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line-soft py-1.5 text-[12.5px] last:border-b-0">
      <span className="text-muted">{label}</span>
      <span className="font-mono tabular-nums text-fg">{children}</span>
    </div>
  );
}
