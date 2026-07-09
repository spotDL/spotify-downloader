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

function AdminReports() {
  const [status, setStatus] = useState<ReportStatus>("pending");
  const reports = useAdminReports(status);

  return (
    <div className="flex flex-col gap-4">
      {/* MERGE: replace with the design-system <SegmentedControl> */}
      <div
        role="radiogroup"
        aria-label="Report status"
        className="inline-flex self-start rounded-md border border-black/10 p-0.5 dark:border-white/15"
      >
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            role="radio"
            aria-checked={status === s}
            onClick={() => setStatus(s)}
            className={`rounded px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
              status === s ? "bg-brand-600 text-white" : "text-muted hover:text-fg"
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
        <ul className="flex flex-col gap-3">
          {reports.data.items.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ReportCard({ report }: { report: ReportResponse }) {
  const [note, setNote] = useState("");
  const approve = useApproveReport();
  const reject = useRejectReport();
  const busy = approve.isPending || reject.isPending;
  const isPending = report.status === "pending";

  return (
    <li className="rounded-card border border-black/10 bg-surface p-4 dark:border-white/10">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="neutral">{report.subject_type}</Badge>
        <span className="font-mono text-sm text-muted">{report.subject_id}</span>
        <Badge tone={STATUS_TONE[report.status]} className="ml-auto capitalize">
          {report.status}
        </Badge>
      </div>
      <dl className="mt-3 flex flex-col gap-1 text-sm">
        {report.field ? (
          <div className="flex gap-2">
            <dt className="text-muted">Field</dt>
            <dd className="font-medium text-fg">{report.field}</dd>
          </div>
        ) : null}
        {report.proposed_value ? (
          <div className="flex gap-2">
            <dt className="text-muted">Proposed</dt>
            <dd className="font-medium text-fg">{report.proposed_value}</dd>
          </div>
        ) : null}
        {report.reason ? (
          <div className="flex gap-2">
            <dt className="text-muted">Reason</dt>
            <dd className="text-fg">{report.reason}</dd>
          </div>
        ) : null}
      </dl>

      {isPending ? (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
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
      ) : null}
    </li>
  );
}
