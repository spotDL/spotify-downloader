// CONTRACT H — ScoreGauge. A 0–1 match score rendered as a color-ramped bar
// (danger → warn → brand) with the community `net_score` as a secondary figure.
// Accessible as an ARIA `meter` (aria-valuenow on the 0–1 scale).

type Tone = "danger" | "warn" | "brand";

const BAR_TONE: Record<Tone, string> = {
  danger: "bg-danger",
  warn: "bg-warn",
  brand: "bg-brand-500",
};

function toneFor(score: number): Tone {
  if (score >= 0.75) return "brand";
  if (score >= 0.5) return "warn";
  return "danger";
}

export function ScoreGauge({
  score,
  netScore,
  className = "",
}: {
  score: number;
  netScore?: number;
  className?: string;
}) {
  const clamped = Math.min(1, Math.max(0, score));
  const pct = Math.round(clamped * 100);
  const tone = toneFor(clamped);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        role="meter"
        aria-label="Match score"
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={clamped}
        aria-valuetext={`${pct}%`}
        className="h-2 w-24 overflow-hidden rounded-full bg-black/10 dark:bg-white/10"
      >
        <div
          className={`h-full rounded-full ${BAR_TONE[tone]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium tabular-nums text-fg">{pct}%</span>
      {netScore !== undefined ? (
        <span
          className="text-xs tabular-nums text-muted"
          title="Community net score"
        >
          {netScore >= 0 ? `+${netScore}` : netScore}
        </span>
      ) : null}
    </div>
  );
}
