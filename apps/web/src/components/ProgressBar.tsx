// CONTRACT H — ProgressBar. A 0–1 determinate bar with a phase label; renders
// indeterminate (animated, no aria-valuenow) when `percent` is null. Accessible
// as an ARIA `progressbar` on a 0–100 scale.

export function ProgressBar({
  percent,
  phase,
  className = "",
}: {
  /** 0–1 completion, or null for an indeterminate (unknown-progress) bar. */
  percent: number | null;
  phase?: string;
  className?: string;
}) {
  const determinate = percent !== null;
  const clamped = determinate ? Math.min(1, Math.max(0, percent)) : 0;
  const pct = Math.round(clamped * 100);

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {phase !== undefined ? (
        <span className="text-xs text-muted">{phase}</span>
      ) : null}
      <div
        role="progressbar"
        aria-label={phase ?? "Progress"}
        aria-valuemin={0}
        aria-valuemax={100}
        // Omit aria-valuenow entirely when indeterminate — the correct ARIA
        // signal for "progress unknown".
        aria-valuenow={determinate ? pct : undefined}
        className="h-2 w-full overflow-hidden rounded-full bg-black/10 dark:bg-white/10"
      >
        {determinate ? (
          <div
            className="h-full rounded-full bg-brand-500 transition-[width]"
            style={{ width: `${pct}%` }}
          />
        ) : (
          <div className="h-full w-1/3 animate-pulse rounded-full bg-brand-500" />
        )}
      </div>
    </div>
  );
}
