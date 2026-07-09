import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
  className = "",
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center gap-2 rounded-card border border-dashed border-black/10 bg-surface px-6 py-12 text-center dark:border-white/10 ${className}`}
    >
      <p className="text-base font-medium text-fg">{title}</p>
      {description ? (
        <p className="max-w-prose text-sm text-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
