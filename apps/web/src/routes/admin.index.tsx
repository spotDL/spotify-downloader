import { createFileRoute } from "@tanstack/react-router";
import type { AdminStatsResponse } from "../api/generated/types.gen";
import { useAdminStats } from "../api/queries";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";

export const Route = createFileRoute("/admin/")({
  component: AdminOverview,
});

// MERGE: replace the stat cards with the design-system <StatCard> grid.
const STAT_FIELDS: { key: keyof AdminStatsResponse; label: string }[] = [
  { key: "users_total", label: "Users" },
  { key: "matches_total", label: "Matches" },
  { key: "community_verified_matches", label: "Verified matches" },
  { key: "rejected_matches", label: "Rejected matches" },
  { key: "votes_total", label: "Votes" },
  { key: "reports_total", label: "Reports" },
  { key: "reports_pending", label: "Reports pending" },
];

function AdminOverview() {
  const stats = useAdminStats();

  if (stats.isPending) return <Spinner label="Loading stats" />;
  if (stats.isError || !stats.data)
    return <ErrorState description="Couldn't load admin stats." />;

  const data = stats.data;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {STAT_FIELDS.map(({ key, label }) => (
        <div
          key={key}
          className="rounded-card border border-black/10 bg-surface p-4 dark:border-white/10"
        >
          <p className="text-sm text-muted">{label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">{data[key]}</p>
        </div>
      ))}
    </div>
  );
}
