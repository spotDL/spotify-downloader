import { useEffect, useState } from "react";
import { cn } from "../lib/utils";

// CONTRACT H — VoteButtons. Up/down toggle reflecting the caller's current vote,
// retracting on a re-click, applied optimistically (local state flips before the
// mutation settles). Disabled with a "sign in to vote" tooltip when the viewer
// can't vote. The actual voteMatch/voteLyrics/voteLink wiring is the caller's
// (Task 7) via `onVote`; this component owns the affordance + optimism only.

export type VoteValue = 1 | 0 | -1;

export function VoteButtons({
  value = 0,
  canVote,
  onVote,
  netScore,
  className,
}: {
  /** The viewer's current vote (1 up, -1 down, 0 none). */
  value?: VoteValue;
  /** Whether the viewer may vote (authed + voting enabled). */
  canVote: boolean;
  /** Called with the next vote value (0 when a vote is retracted). */
  onVote?: (next: VoteValue) => void;
  netScore?: number;
  className?: string;
}) {
  // Optimistic local mirror of the server vote; re-syncs if the prop changes.
  const [optimistic, setOptimistic] = useState<VoteValue>(value);
  useEffect(() => setOptimistic(value), [value]);

  const cast = (direction: 1 | -1) => {
    const next: VoteValue = optimistic === direction ? 0 : direction;
    setOptimistic(next);
    onVote?.(next);
  };

  const tooltip = canVote ? undefined : "Sign in to vote";
  const buttonBase =
    "rounded px-1.5 py-0.5 text-sm text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <div role="group" aria-label="Vote" className={cn("flex items-center gap-1", className)}>
      <button
        type="button"
        aria-label="Upvote"
        aria-pressed={optimistic === 1}
        disabled={!canVote}
        title={tooltip}
        onClick={() => cast(1)}
        className={cn(buttonBase, "aria-pressed:text-primary")}
      >
        ▲
      </button>
      {netScore !== undefined ? (
        <span aria-live="polite" className="min-w-6 text-center text-xs tnum text-foreground">
          {netScore >= 0 ? `+${netScore}` : netScore}
        </span>
      ) : null}
      <button
        type="button"
        aria-label="Downvote"
        aria-pressed={optimistic === -1}
        disabled={!canVote}
        title={tooltip}
        onClick={() => cast(-1)}
        className={cn(buttonBase, "aria-pressed:text-destructive")}
      >
        ▼
      </button>
    </div>
  );
}
