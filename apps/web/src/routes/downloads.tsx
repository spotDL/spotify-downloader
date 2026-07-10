import { createFileRoute } from "@tanstack/react-router";
import type { DownloadJobOut, DownloadStatus } from "../api/generated/types.gen";
import {
  downloadFileUrl,
  useCancelDownload,
  useDownloads,
  useSubmitDownload,
} from "../api/downloads";
import { useProgressSocket } from "../api/ws";
import { useFeature } from "../app/config";
import { isApiError } from "../api/errors";
import { joinArtists } from "../lib/format";
import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { ProgressBar } from "../components/ProgressBar";
import { SectionDivider } from "../components/SectionDivider";
import { Spinner } from "../components/Spinner";
import { toast } from "../components/Toasts";
import { DownloadIcon, NoteIcon, RefreshIcon } from "../components/icons";

export const Route = createFileRoute("/downloads")({ component: DownloadsPage });

function DownloadsPage() {
  // CONTRACT G — the route exists in every mode, but the queue only renders
  // where downloads are enabled (a direct-URL visit in HOSTED is a dead end).
  if (!useFeature("downloads")) {
    return (
      <div className="mx-auto w-full max-w-[1080px] px-6 py-16">
        <EmptyState
          title="Downloads"
          description="Downloads are disabled on this server."
        />
      </div>
    );
  }
  return <DownloadsQueue />;
}

// Split out so the live socket + query hooks mount only when downloads are on.
function DownloadsQueue() {
  useProgressSocket();
  // Active + recent jobs, newest-first (the server default order); completed
  // rows also live in the Library. Live WS frames patch these rows in place.
  const query = useDownloads({ limit: 100 });

  return (
    <div className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 py-7">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-fg">Downloads</h1>
        <p className="text-sm text-muted">
          Live queue — active, waiting, and recently finished jobs.
        </p>
      </div>

      {query.isPending ? (
        <div className="flex justify-center py-16">
          <Spinner label="Loading the queue" className="size-8" />
        </div>
      ) : query.isError ? (
        <ErrorState
          description="Couldn't load the download queue."
          action={
            <Button variant="secondary" onClick={() => void query.refetch()}>
              Retry
            </Button>
          }
        />
      ) : query.data.jobs.length === 0 ? (
        <EmptyState
          title="Nothing in the queue"
          description="Search to add a track, album, or playlist — it shows up here as it downloads."
        />
      ) : (
        <>
          <SummaryStrip jobs={query.data.jobs} />
          <QueueGroups jobs={query.data.jobs} />
        </>
      )}
    </div>
  );
}

// ── Status vocabulary ────────────────────────────────────────────────────────
type Tone = "neutral" | "brand" | "warn" | "danger" | "muted";

const STATUS_META: Record<
  DownloadStatus,
  { label: string; tone: Tone; dot: string }
> = {
  queued: { label: "Queued", tone: "muted", dot: "bg-muted" },
  running: { label: "Downloading", tone: "warn", dot: "bg-gold" },
  completed: { label: "Completed", tone: "brand", dot: "bg-emerald" },
  failed: { label: "Failed", tone: "danger", dot: "bg-red" },
  cancelled: { label: "Cancelled", tone: "muted", dot: "bg-muted" },
};

// ── Summary strip ────────────────────────────────────────────────────────────
function SummaryStrip({ jobs }: { jobs: DownloadJobOut[] }) {
  const active = jobs.filter((j) => j.status === "running").length;
  const queued = jobs.filter((j) => j.status === "queued").length;
  const done = jobs.filter((j) => j.status === "completed").length;
  const failed = jobs.filter((j) => j.status === "failed").length;

  // Overall progress: completed jobs count as done, running jobs contribute
  // their live fraction. Queued/cancelled/failed contribute nothing.
  const overall =
    jobs.length === 0
      ? 0
      : jobs.reduce((sum, j) => {
          if (j.status === "completed") return sum + 1;
          if (j.status === "running") return sum + j.progress;
          return sum;
        }, 0) / jobs.length;

  return (
    <section className="flex flex-col gap-3.5 rounded-card border border-line-soft bg-surface px-5 py-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Stat label="Active" value={active} accent="text-gold" />
        <Stat label="Queued" value={queued} accent="text-ink-2" />
        <Stat label="Done" value={done} accent="text-emerald" />
        <Stat label="Failed" value={failed} accent="text-red" />
        <span className="ml-auto font-mono text-xs tabular-nums text-muted">
          {Math.round(overall * 100)}%
        </span>
      </div>
      <ProgressBar percent={overall} phase="Overall" />
    </section>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-[11px] uppercase tracking-wide text-muted">
        {label}
      </span>
      <span className={`font-mono text-lg font-semibold tabular-nums ${accent}`}>
        {value}
      </span>
    </span>
  );
}

// ── Batch groups ─────────────────────────────────────────────────────────────
type Group = {
  batchId: string | null;
  batchName: string | null;
  batchKind: string | null;
  jobs: DownloadJobOut[];
};

function groupByBatch(jobs: DownloadJobOut[]): Group[] {
  const order: string[] = [];
  const groups = new Map<string, Group>();
  for (const job of jobs) {
    const key = job.batch_id ?? `job:${job.id}`;
    let group = groups.get(key);
    if (!group) {
      group = {
        batchId: job.batch_id,
        batchName: job.batch_name,
        batchKind: job.batch_kind,
        jobs: [],
      };
      groups.set(key, group);
      order.push(key);
    }
    group.jobs.push(job);
  }
  return order.map((key) => groups.get(key)!);
}

function QueueGroups({ jobs }: { jobs: DownloadJobOut[] }) {
  return (
    <div className="flex flex-col gap-6">
      {groupByBatch(jobs).map((group) => {
        // A multi-track batch is headed by its real name (kind-prefixed) when the
        // server knows it, falling back to the track count for an unnamed batch.
        const multi = group.jobs.length > 1;
        const title = group.batchName
          ? group.batchKind
            ? `${group.batchKind} · ${group.batchName}`
            : group.batchName
          : `${group.jobs.length} tracks`;
        return (
          <section
            key={group.batchId ?? group.jobs[0].id}
            className="flex flex-col gap-2"
          >
            {multi ? (
              <div className="flex items-center gap-3">
                <SectionDivider title={title} accent="teal" />
                <span className="font-mono text-[11px] text-ink-4">
                  {group.jobs.length} tracks
                </span>
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
        );
      })}
    </div>
  );
}

// ── Job row ──────────────────────────────────────────────────────────────────
function JobRow({ job }: { job: DownloadJobOut }) {
  const cancel = useCancelDownload();
  const retry = useSubmitDownload();
  const meta = STATUS_META[job.status];

  const cancellable = job.status === "queued" || job.status === "running";
  const showProgress = job.status === "queued" || job.status === "running";
  const skipped = job.status === "completed" && job.skip_reason != null;
  const completedFile =
    job.status === "completed" && !job.skip_reason && job.output_path != null;
  // No dedicated retry endpoint — re-submitting the track id re-enqueues it.
  const retryable = job.status === "failed" && job.track_id != null;

  return (
    <div className="group flex flex-col gap-2 rounded-card border border-line-soft bg-surface px-3 py-2.5 transition-colors hover:border-line">
      <div className="flex items-center gap-3">
        {/* The job's album cover when known, else the note-glyph placeholder. */}
        <span className="size-11 shrink-0 overflow-hidden rounded-lg ring-1 ring-white/5">
          {job.cover_url ? (
            <img
              src={job.cover_url}
              alt=""
              className="size-full object-cover"
            />
          ) : (
            <span className="grid size-full place-items-center bg-elevated text-muted">
              <NoteIcon className="size-5" />
            </span>
          )}
        </span>

        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <p className="truncate text-[13px] font-medium text-fg">
            {job.track_name ?? "Unknown track"}
          </p>
          {job.artists.length > 0 ? (
            <p className="truncate text-[11px] text-muted">
              {joinArtists(job.artists)}
            </p>
          ) : null}
        </div>

        <span
          className={`size-2 shrink-0 rounded-full ${meta.dot} ${
            job.status === "running" ? "animate-pulse" : ""
          }`}
          aria-hidden
        />
        <Badge tone={skipped ? "warn" : meta.tone}>
          {skipped ? "Skipped" : meta.label}
        </Badge>

        <div className="flex items-center gap-1.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
          {completedFile ? (
            <a
              href={downloadFileUrl(job.id)}
              download
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-emerald hover:bg-elevated"
            >
              <DownloadIcon className="size-3.5" />
              Download
            </a>
          ) : null}
          {retryable ? (
            <Button
              variant="ghost"
              className="px-2 py-1 text-xs"
              disabled={retry.isPending}
              onClick={() =>
                retry.mutate(
                  { body: { query: job.track_id! } },
                  {
                    onSuccess: () => toast.info("Re-queued the download."),
                    onError: (error) => {
                      if (isApiError(error)) toast.fromApiError(error);
                      else toast.error("Couldn't retry the download.");
                    },
                  },
                )
              }
            >
              <RefreshIcon className="size-3.5" />
              Retry
            </Button>
          ) : null}
          {cancellable ? (
            <Button
              variant="ghost"
              className="px-2 py-1 text-xs"
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
      </div>

      {showProgress ? <ProgressBar percent={job.progress} /> : null}
      {job.status === "failed" && job.error_message ? (
        <p className="font-mono text-[11px] text-red">{job.error_message}</p>
      ) : null}
    </div>
  );
}
