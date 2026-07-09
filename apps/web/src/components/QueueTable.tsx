import type { DownloadJobOut, DownloadStatus } from "../api/generated/types.gen";
import {
  batchSaveFileUrl,
  downloadFileUrl,
  useCancelDownload,
} from "../api/downloads";
import { isApiError } from "../api/errors";
import { Badge } from "./Badge";
import { Button } from "./Button";
import { ProgressBar } from "./ProgressBar";
import { toast } from "./Toasts";

// MERGE: this is the finalized queue table but its atoms (Badge, ProgressBar,
// Button) are local placeholders pending the design-system versions (CONTRACT
// H / Plan 10 Task 5, sibling track).

type Tone = "neutral" | "brand" | "warn" | "danger" | "muted";

const STATUS_META: Record<DownloadStatus, { label: string; tone: Tone }> = {
  queued: { label: "Queued", tone: "muted" },
  running: { label: "Downloading", tone: "brand" },
  completed: { label: "Completed", tone: "brand" },
  failed: { label: "Failed", tone: "danger" },
  cancelled: { label: "Cancelled", tone: "muted" },
};

type Group = { batchId: string | null; jobs: DownloadJobOut[] };

function groupByBatch(jobs: DownloadJobOut[]): Group[] {
  const order: string[] = [];
  const groups = new Map<string, Group>();
  for (const job of jobs) {
    const key = job.batch_id ?? `job:${job.id}`;
    let group = groups.get(key);
    if (!group) {
      group = { batchId: job.batch_id, jobs: [] };
      groups.set(key, group);
      order.push(key);
    }
    group.jobs.push(job);
  }
  return order.map((key) => groups.get(key)!);
}

/**
 * The download queue / library table, grouped by submission batch. Each row
 * shows status, a live progress bar (queued/running), a Cancel action (still
 * cancellable), and a file link (completed). `showBatchSaveFile` adds the
 * per-batch `.spotdl` save-file download (the library view).
 */
export function QueueTable({
  jobs,
  showBatchSaveFile = false,
}: {
  jobs: DownloadJobOut[];
  showBatchSaveFile?: boolean;
}) {
  return (
    <div className="flex flex-col gap-6">
      {groupByBatch(jobs).map((group) => (
        <section
          key={group.batchId ?? group.jobs[0].id}
          className="flex flex-col gap-2"
        >
          {group.jobs.length > 1 || (showBatchSaveFile && group.batchId) ? (
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-medium text-muted">
                {group.jobs.length} {group.jobs.length === 1 ? "track" : "tracks"}
              </h2>
              {showBatchSaveFile && group.batchId ? (
                <a
                  href={batchSaveFileUrl(group.batchId)}
                  className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-100"
                >
                  Save file (.spotdl)
                </a>
              ) : null}
            </div>
          ) : null}
          <ul className="flex flex-col gap-2">
            {group.jobs.map((job) => (
              <li key={job.id}>
                <JobRow job={job} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function JobRow({ job }: { job: DownloadJobOut }) {
  const cancel = useCancelDownload();
  const meta = STATUS_META[job.status];
  const cancellable = job.status === "queued" || job.status === "running";
  const showProgress = job.status === "queued" || job.status === "running";
  const skipped = job.status === "completed" && job.skip_reason != null;
  const completedFile =
    job.status === "completed" && !job.skip_reason && job.output_path != null;

  return (
    <div className="flex flex-col gap-2 rounded-card border border-black/10 bg-surface px-3 py-2 dark:border-white/10">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-fg">
            {job.track_name ?? "Unknown track"}
          </p>
          {job.artists.length > 0 ? (
            <p className="truncate text-sm text-muted">
              {job.artists.join(", ")}
            </p>
          ) : null}
        </div>
        <Badge tone={skipped ? "warn" : meta.tone}>
          {skipped ? "Skipped" : meta.label}
        </Badge>
        {completedFile ? (
          <a
            href={downloadFileUrl(job.id)}
            download
            className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-100"
          >
            Download
          </a>
        ) : null}
        {cancellable ? (
          <Button
            variant="ghost"
            disabled={cancel.isPending}
            onClick={() =>
              cancel.mutate(
                { path: { job_id: job.id } },
                {
                  onError: (error) => {
                    if (isApiError(error)) toast.fromApiError(error);
                    else toast.error("Couldn't cancel the download.");
                  },
                },
              )
            }
          >
            Cancel
          </Button>
        ) : null}
      </div>
      {showProgress ? (
        <ProgressBar
          value={job.progress}
          label={`${job.track_name ?? "Track"} progress`}
        />
      ) : null}
      {job.status === "failed" && job.error_message ? (
        <p className="text-sm text-danger">{job.error_message}</p>
      ) : null}
    </div>
  );
}
