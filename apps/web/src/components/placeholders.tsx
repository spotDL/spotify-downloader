// Minimal local stand-ins for the design-system components being built on a
// concurrent track. Each export is marked `// MERGE:` so the integrator can
// swap it for the real component wholesale. They are intentionally plain: just
// enough structure + accessible roles for the routes (and their tests) to work.
import type { ReactNode } from "react";
import { Badge } from "./Badge";

/** A 0..1 match score rendered as a percentage. */
// MERGE: replace with design-system <ScoreGauge>
export function ScoreGauge({
  score,
  className = "",
}: {
  score: number;
  className?: string;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <span
      role="meter"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Match score ${pct}%`}
      className={`inline-flex min-w-[3ch] items-center justify-center rounded-md bg-brand-100 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-brand-700 dark:bg-brand-700/30 dark:text-brand-100 ${className}`}
    >
      {pct}%
    </span>
  );
}

/** A presentational result/entity card (caller wraps it in the target Link). */
// MERGE: replace with design-system <EntityCard>
export function EntityCard({
  title,
  subtitle,
  imageUrl,
  badge,
}: {
  title: string;
  subtitle?: ReactNode;
  imageUrl?: string | null;
  badge?: ReactNode;
}) {
  return (
    <div className="flex h-full flex-col gap-3 rounded-card border border-black/10 bg-surface p-3 shadow-card transition-colors hover:border-brand-500/50 dark:border-white/10">
      <div className="aspect-square w-full overflow-hidden rounded-md bg-black/5 dark:bg-white/10">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt=""
            loading="lazy"
            className="size-full object-cover"
          />
        ) : null}
      </div>
      <div className="flex flex-col gap-1">
        <p className="truncate text-sm font-medium text-fg" title={title}>
          {title}
        </p>
        {subtitle ? (
          <p className="truncate text-xs text-muted">{subtitle}</p>
        ) : null}
        {badge ? <div>{badge}</div> : null}
      </div>
    </div>
  );
}

export type VoteValue = "up" | "down" | "retract";

/**
 * Up/down vote control. `yourVote` is +1 / -1 / null (the caller's current
 * vote). Clicking the already-active direction retracts. When `disabled`, both
 * buttons are inert and carry `disabledReason` as a native tooltip (CONTRACT —
 * anonymous users see the control but can't act).
 */
// MERGE: replace with design-system <VoteButtons>
export function VoteButtons({
  netScore,
  yourVote,
  disabled = false,
  disabledReason,
  onVote,
}: {
  netScore: number;
  yourVote?: number | null;
  disabled?: boolean;
  disabledReason?: string;
  onVote: (value: VoteValue) => void;
}) {
  const up = yourVote === 1;
  const down = yourVote === -1;
  const activeClass = "text-brand-600";
  const idleClass = "text-muted hover:text-fg";
  return (
    <div
      className="inline-flex items-center gap-1"
      title={disabled ? disabledReason : undefined}
    >
      <button
        type="button"
        aria-label="Upvote"
        aria-pressed={up}
        disabled={disabled}
        onClick={() => onVote(up ? "retract" : "up")}
        className={`rounded p-0.5 text-sm disabled:cursor-not-allowed disabled:opacity-50 ${up ? activeClass : idleClass}`}
      >
        ▲
      </button>
      <span className="min-w-[2ch] text-center text-sm tabular-nums text-fg">
        {netScore}
      </span>
      <button
        type="button"
        aria-label="Downvote"
        aria-pressed={down}
        disabled={disabled}
        onClick={() => onVote(down ? "retract" : "down")}
        className={`rounded p-0.5 text-sm disabled:cursor-not-allowed disabled:opacity-50 ${down ? activeClass : idleClass}`}
      >
        ▼
      </button>
    </div>
  );
}

const STATUS_TONE = {
  auto: "neutral",
  community_verified: "brand",
  rejected: "danger",
} as const;

const STATUS_LABEL = {
  auto: "Auto",
  community_verified: "Verified",
  rejected: "Rejected",
} as const;

/** A match's status as a labelled badge. */
export function MatchStatusBadge({
  status,
}: {
  status: keyof typeof STATUS_LABEL;
}) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>;
}
