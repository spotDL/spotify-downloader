import type { ReactNode } from "react";

export function ErrorState({
  title = "Something went wrong",
  description,
  action,
  className = "",
}: {
  title?: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center gap-2 rounded-card border border-danger/30 bg-danger/5 px-6 py-12 text-center ${className}`}
    >
      <p className="text-base font-medium text-danger">{title}</p>
      {description ? (
        <p className="max-w-prose text-sm text-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
