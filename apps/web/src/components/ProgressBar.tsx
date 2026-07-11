import { cn } from "../lib/utils";

// CONTRACT H — ProgressBar. A 0–1 determinate bar with a phase label; renders
// indeterminate (pulsing, no aria-valuenow) when `percent` is null. Rendered in
// the Control Room segmented-meter language while remaining an ARIA
// `progressbar` on a 0–100 scale.

const CELLS = 16;

export function ProgressBar({
  percent,
  phase,
  className,
}: {
  /** 0–1 completion, or null for an indeterminate (unknown-progress) bar. */
  percent: number | null;
  phase?: string;
  className?: string;
}) {
  const determinate = percent !== null;
  const clamped = determinate ? Math.min(1, Math.max(0, percent)) : 0;
  const pct = Math.round(clamped * 100);
  const lit = determinate ? Math.round(clamped * CELLS) : 0;
  const inFlight = determinate && pct > 0 && pct < 100;

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {phase !== undefined ? (
        <span className="text-xs text-muted-foreground">{phase}</span>
      ) : null}
      <div
        role="progressbar"
        aria-label={phase ?? "Progress"}
        aria-valuemin={0}
        aria-valuemax={100}
        // Omit aria-valuenow entirely when indeterminate — the correct ARIA
        // signal for "progress unknown".
        aria-valuenow={determinate ? pct : undefined}
        className="meter h-2 w-full"
        style={{ ["--meter-cells" as string]: CELLS }}
      >
        {Array.from({ length: CELLS }, (_, i) => (
          <span
            key={i}
            className="meter-cell"
            data-lit={(determinate && i < lit) || undefined}
            data-active={(!determinate || (inFlight && i === lit - 1)) || undefined}
          />
        ))}
      </div>
    </div>
  );
}
