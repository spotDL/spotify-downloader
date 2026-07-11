import { cn } from "../lib/utils";
import { scoreColor } from "./ui/meter";

// CONTRACT H (rebuild) — VuGauge. A 0–1 match score rendered in the Control
// Room segmented-meter language, threshold-coloured via `scoreColor` (≥75
// success / ≥45 warning / else destructive). Exposed as an ARIA `meter`
// (aria-valuenow on the 0–1 scale, aria-valuetext the percentage) so the
// score-scale regression (0–100 wire → /100 here) stays observable.

const CELLS = 12;

export function VuGauge({
  score,
  size = 52,
  className,
}: {
  score: number;
  size?: number;
  className?: string;
}) {
  const clamped = Math.min(1, Math.max(0, score));
  const pct = Math.round(clamped * 100);
  const color = scoreColor(pct);
  const lit = Math.round(clamped * CELLS);

  return (
    <div
      role="meter"
      aria-label="Match score"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={clamped}
      aria-valuetext={`${pct}%`}
      className={cn("inline-flex shrink-0 items-center gap-2", className)}
    >
      <span
        className="meter h-2"
        style={{
          width: size,
          ["--meter-cells" as string]: CELLS,
          ["--meter-color" as string]: color,
        }}
      >
        {Array.from({ length: CELLS }, (_, i) => (
          <span key={i} className="meter-cell" data-lit={i < lit || undefined} />
        ))}
      </span>
      <span className="font-mono text-xs font-bold tnum" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}
