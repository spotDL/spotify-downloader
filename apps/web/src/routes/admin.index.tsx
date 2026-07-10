import { createFileRoute } from "@tanstack/react-router";
import type { AdminStatsResponse } from "../api/generated/types.gen";
import { useAdminStats } from "../api/queries";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";

export const Route = createFileRoute("/admin/")({
  component: AdminOverview,
});

const STAT_FIELDS: {
  key: keyof AdminStatsResponse;
  label: string;
  accent: string;
}[] = [
  { key: "users_total", label: "Users", accent: "text-fg" },
  { key: "matches_total", label: "Matches", accent: "text-fg" },
  {
    key: "community_verified_matches",
    label: "Verified matches",
    accent: "text-emerald",
  },
  { key: "rejected_matches", label: "Rejected matches", accent: "text-red" },
  { key: "votes_total", label: "Votes", accent: "text-teal" },
  { key: "reports_total", label: "Reports", accent: "text-fg" },
  { key: "reports_pending", label: "Reports pending", accent: "text-gold" },
];

function AdminOverview() {
  const stats = useAdminStats();

  if (stats.isPending) return <Spinner label="Loading stats" />;
  if (stats.isError || !stats.data)
    return <ErrorState description="Couldn't load admin stats." />;

  const data = stats.data;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {STAT_FIELDS.map(({ key, label, accent }) => (
        <div
          key={key}
          className="hover-lift flex flex-col gap-1 rounded-card border border-line-soft bg-surface p-4"
        >
          <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
          <p className={`font-mono text-3xl font-semibold tabular-nums ${accent}`}>
            {data[key]}
          </p>
        </div>
      ))}
    </div>
  );
}
