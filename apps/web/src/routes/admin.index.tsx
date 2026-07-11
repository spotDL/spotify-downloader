import { createFileRoute } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import type { AdminStatsResponse } from "../api/generated/types.gen";
import { useAdminStats } from "../api/queries";
import { StatChip } from "../components/StatChip";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { cn } from "../lib/utils";

export const Route = createFileRoute("/admin/")({
  component: AdminOverview,
});

const STAT_FIELDS: {
  key: keyof AdminStatsResponse;
  label: string;
  accent: string;
}[] = [
  { key: "users_total", label: "Users", accent: "text-foreground" },
  { key: "matches_total", label: "Matches", accent: "text-foreground" },
  {
    key: "community_verified_matches",
    label: "Verified matches",
    accent: "text-success",
  },
  { key: "rejected_matches", label: "Rejected matches", accent: "text-destructive" },
  { key: "votes_total", label: "Votes", accent: "text-info" },
  { key: "reports_total", label: "Reports", accent: "text-foreground" },
  { key: "reports_pending", label: "Reports pending", accent: "text-warning" },
];

// A subtle one-shot stagger across the stat tiles (respecting reduce-motion).
const grid = { hidden: {}, show: { transition: { staggerChildren: 0.03 } } };
const tile = {
  hidden: { opacity: 0, y: 6 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] as const },
  },
};

function AdminOverview() {
  const reduceMotion = useReducedMotion();
  const stats = useAdminStats();

  if (stats.isPending) return <Spinner label="Loading stats" />;
  if (stats.isError || !stats.data)
    return <ErrorState description="Couldn't load admin stats." />;

  const data = stats.data;

  return (
    <motion.div
      variants={reduceMotion ? undefined : grid}
      initial={reduceMotion ? false : "hidden"}
      animate="show"
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
    >
      {STAT_FIELDS.map(({ key, label, accent }) => (
        <motion.div
          key={key}
          variants={reduceMotion ? undefined : tile}
          className="rounded-lg border border-border bg-card px-4 py-3.5"
        >
          <StatChip label={label} className="flex-col items-start gap-1.5">
            <span className={cn("font-mono text-2xl font-semibold tnum", accent)}>
              {data[key]}
            </span>
          </StatChip>
        </motion.div>
      ))}
    </motion.div>
  );
}
