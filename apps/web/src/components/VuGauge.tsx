// CONTRACT H (rebuild) — VuGauge. A 0–1 match score drawn as a circular VU
// meter, threshold-coloured emerald ≥.90 / gold ≥.70 / red below. Exposed as an
// ARIA `meter` (aria-valuenow on the 0–1 scale, aria-valuetext the percentage)
// so the score-scale regression (0–100 wire → /100 here) stays observable.

type Tone = "emerald" | "gold" | "red";

const STROKE: Record<Tone, string> = {
  emerald: "stroke-emerald",
  gold: "stroke-gold",
  red: "stroke-red",
};
const TEXT: Record<Tone, string> = {
  emerald: "text-emerald",
  gold: "text-gold",
  red: "text-red",
};

function toneFor(score: number): Tone {
  if (score >= 0.9) return "emerald";
  if (score >= 0.7) return "gold";
  return "red";
}

const RADIUS = 22;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function VuGauge({
  score,
  size = 52,
  className = "",
}: {
  score: number;
  size?: number;
  className?: string;
}) {
  const clamped = Math.min(1, Math.max(0, score));
  const pct = Math.round(clamped * 100);
  const tone = toneFor(clamped);
  const dashoffset = CIRCUMFERENCE * (1 - clamped);

  return (
    <div
      role="meter"
      aria-label="Match score"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={clamped}
      aria-valuetext={`${pct}%`}
      className={`relative shrink-0 ${className}`}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 52 52" className="block size-full">
        <circle
          cx="26"
          cy="26"
          r={RADIUS}
          fill="none"
          className="stroke-white/10"
          strokeWidth="5"
        />
        <circle
          cx="26"
          cy="26"
          r={RADIUS}
          fill="none"
          className={STROKE[tone]}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashoffset}
          transform="rotate(-90 26 26)"
        />
      </svg>
      <span
        className={`absolute inset-0 grid place-items-center font-mono text-xs font-bold tabular-nums ${TEXT[tone]}`}
      >
        {pct}%
      </span>
    </div>
  );
}
