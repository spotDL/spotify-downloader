import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import type { ReportResponse, ReportStatus } from "../api/generated/types.gen";
import { useAdminReports, useApproveReport, useRejectReport } from "../api/queries";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";

export const Route = createFileRoute("/admin/reports")({
  component: AdminReports,
});

const STATUSES: ReportStatus[] = ["pending", "approved", "rejected"];

const STATUS_TONE: Record<ReportStatus, "warn" | "brand" | "danger"> = {
  pending: "warn",
  approved: "brand",
  rejected: "danger",
};

const TH = "px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-faint";
const TD = "px-4 py-2.5 align-top";

function AdminReports() {
  const [status, setStatus] = useState<ReportStatus>("pending");
  const reports = useAdminReports(status);

  return (
    <div className="flex flex-col gap-4">
      <div
        role="radiogroup"
        aria-label="Report status"
        className="inline-flex self-start rounded-lg border border-border bg-surface p-0.5"
      >
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            role="radio"
            aria-checked={status === s}
            onClick={() => setStatus(s)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${
              status === s
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {reports.isPending ? <Spinner label="Loading reports" /> : null}
      {reports.isError ? <ErrorState description="Couldn't load the report queue." /> : null}
      {reports.data && reports.data.items.length === 0 ? (
        <EmptyState title="Nothing here" description={`No ${status} reports.`} />
      ) : null}
      {reports.data && reports.data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-surface">
              <tr className="border-b border-border">
                <th className={TH}>Subject</th>
                <th className={TH}>Field</th>
                <th className={TH}>Proposed</th>
                <th className={TH}>Reason</th>
                <th className={TH}>Reported</th>
                <th className={TH}>Status</th>
              </tr>
            </thead>
            <tbody>
              {reports.data.items.map((report) => (
                <ReportRow key={report.id} report={report} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function ReportRow({ report }: { report: ReportResponse }) {
  const [note, setNote] = useState("");
  const approve = useApproveReport();
  const reject = useRejectReport();
  const busy = approve.isPending || reject.isPending;
  const isPending = report.status === "pending";

  return (
    <>
      <tr className="border-t border-border">
        <td className={TD}>
          <div className="flex items-center gap-2">
            <Badge tone="neutral" className="capitalize">
              {report.subject_type}
            </Badge>
            <span className="font-mono text-xs text-muted-foreground tnum">
              {report.subject_id}
            </span>
          </div>
        </td>
        <td className={`${TD} font-mono text-xs text-foreground tnum`}>
          {report.field ?? <span className="text-faint">—</span>}
        </td>
        <td className={TD}>
          {report.proposed_value ? (
            <span className="font-medium text-success">{report.proposed_value}</span>
          ) : (
            <span className="text-faint">—</span>
          )}
        </td>
        <td className={`${TD} text-muted-foreground`}>
          {report.reason ?? <span className="text-faint">—</span>}
        </td>
        <td className={`${TD} font-mono text-xs text-muted-foreground tnum`}>
          {new Date(report.created_at).toLocaleDateString()}
        </td>
        <td className={TD}>
          <Badge tone={STATUS_TONE[report.status]} className="capitalize">
            {report.status}
          </Badge>
        </td>
      </tr>
      {isPending ? (
        <tr className="border-t border-border/60 bg-surface/40">
          <td colSpan={6} className="px-4 py-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <Input
                aria-label={`Review note for report ${report.id}`}
                placeholder="Optional note…"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="sm:flex-1"
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    approve.mutate({ reportId: report.id, note: note.trim() || undefined })
                  }
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  disabled={busy}
                  onClick={() =>
                    reject.mutate({ reportId: report.id, note: note.trim() || undefined })
                  }
                >
                  Reject
                </Button>
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}
