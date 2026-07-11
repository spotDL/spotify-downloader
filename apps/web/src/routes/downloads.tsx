import { createFileRoute } from "@tanstack/react-router";
import {
  AlertCircle,
  Ban,
  Download,
  ListMusic,
  Music,
  RotateCcw,
} from "lucide-react";
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
import { cn } from "../lib/utils";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { Meter } from "../components/ui/meter";
import { toast } from "../components/Toasts";

export const Route = createFileRoute("/downloads")({ component: DownloadsPage });

function DownloadsPage() {
  // CONTRACT G — the route exists in every mode, but the queue only renders
  // where downloads are enabled (a direct-URL visit in HOSTED is a dead end).
  if (!useFeature("downloads")) {
    return (
      <EmptyState
        icon={<Music aria-hidden />}
        title="Downloads"
        description="Downloads are disabled on this server."
      />
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
    <div className="flex max-w-3xl flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-faint">
          Console
        </p>
        <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">
          Download queue
        </h1>
        <p className="text-sm text-muted-foreground">
          Live queue — active, waiting, and recently finished jobs.
        </p>
      </header>

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
          icon={<ListMusic aria-hidden />}
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
const STATUS_META: Record<DownloadStatus, { label: string; className: string }> =
  {
    queued: { label: "Queued", className: "text-faint" },
    running: { label: "Downloading", className: "text-primary" },
    completed: { label: "Completed", className: "text-success" },
    failed: { label: "Failed", className: "text-destructive" },
    cancelled: { label: "Cancelled", className: "text-muted-foreground" },
  };

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

/** Meter appearance for a channel row — the only progress visualization. */
function meterFor(job: DownloadJobOut): {
  value: number;
  active: boolean;
  color?: string;
} {
  const pct = Math.round(clamp01(job.progress) * 100);
  switch (job.status) {
    case "completed":
      return { value: 100, active: false, color: "var(--success)" };
    case "failed":
      return { value: pct, active: false, color: "var(--destructive)" };
    case "cancelled":
      return { value: pct, active: false, color: "var(--muted-foreground)" };
    case "running":
      return { value: pct, active: true };
    default:
      return { value: pct, active: false };
  }
}

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
          if (j.status === "running") return sum + clamp01(j.progress);
          return sum;
        }, 0) / jobs.length;

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <Stat label="Active" value={active} accent="text-primary" />
        <Stat label="Queued" value={queued} accent="text-muted-foreground" />
        <Stat label="Done" value={done} accent="text-success" />
        <Stat label="Failed" value={failed} accent="text-destructive" />
        <span className="ml-auto font-mono text-xs tnum text-muted-foreground">
          {Math.round(overall * 100)}%
        </span>
      </div>
      <Meter
        value={Math.round(overall * 100)}
        max={100}
        cells={16}
        label="Overall"
      />
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
      <span className="text-xs font-medium uppercase tracking-wider text-faint">
        {label}
      </span>
      <span className={cn("font-mono text-lg font-semibold tnum", accent)}>
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
              <div className="flex items-center gap-3 border-b border-border pb-2">
                <span className="truncate text-xs font-medium uppercase tracking-wider text-faint">
                  {title}
                </span>
                <span className="ml-auto font-mono text-xs tnum text-muted-foreground">
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

// ── Channel row ──────────────────────────────────────────────────────────────
function JobRow({ job }: { job: DownloadJobOut }) {
  const cancel = useCancelDownload();
  const retry = useSubmitDownload();
  const meta = STATUS_META[job.status];
  const meter = meterFor(job);
  const title = job.track_name ?? "Unknown track";

  const inFlight = job.status === "running";
  const isFailed = job.status === "failed";
  const cancellable = job.status === "queued" || job.status === "running";
  const skipped = job.status === "completed" && job.skip_reason != null;
  const completedFile =
    job.status === "completed" && !job.skip_reason && job.output_path != null;
  // No dedicated retry endpoint — re-submitting the track id re-enqueues it.
  const retryable = job.status === "failed" && job.track_id != null;
  const pct = Math.round(clamp01(job.progress) * 100);
  const showPercent = job.status === "running" || job.status === "completed";

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card transition-colors hover:border-faint/50",
        inFlight && "border-primary/30",
        isFailed && "border-l-2 border-l-destructive",
      )}
    >
      <div className="flex items-center gap-4 px-3 py-2.5">
        {/* The job's album cover when known, else the note-glyph placeholder. */}
        <span className="size-10 shrink-0 overflow-hidden rounded-md border border-border">
          {job.cover_url ? (
            <img src={job.cover_url} alt="" className="size-full object-cover" />
          ) : (
            <span className="grid size-full place-items-center bg-elevated text-faint">
              <Music className="size-5" aria-hidden />
            </span>
          )}
        </span>

        {/* Identity */}
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <p
            className={cn(
              "text-[10px] font-medium uppercase tracking-wider",
              meta.className,
            )}
          >
            {skipped ? "Skipped" : meta.label}
          </p>
          <p className="truncate text-sm font-medium text-foreground">{title}</p>
          {job.artists.length > 0 ? (
            <p className="truncate text-xs text-muted-foreground">
              {joinArtists(job.artists)}
            </p>
          ) : null}
        </div>

        {/* Meter — 16-cell segmented, the only progress visualization */}
        <div className="hidden w-28 shrink-0 sm:block md:w-36">
          <Meter
            cells={16}
            value={meter.value}
            max={100}
            active={meter.active}
            color={meter.color}
            label="Progress"
          />
        </div>

        {/* Mono readout */}
        <div className="hidden w-12 shrink-0 flex-col items-end font-mono text-xs tnum sm:flex">
          {showPercent ? (
            <span className="text-foreground">{pct}%</span>
          ) : (
            <span className="text-faint">—</span>
          )}
        </div>

        {/* Row actions */}
        <div className="flex shrink-0 items-center gap-0.5">
          {completedFile ? (
            <a
              href={downloadFileUrl(job.id)}
              download
              aria-label={`Download ${title}`}
              className="inline-flex size-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Download className="size-4" />
            </a>
          ) : null}
          {retryable ? (
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Retry ${title}`}
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
              <RotateCcw className="size-4" />
            </Button>
          ) : null}
          {cancellable ? (
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Cancel ${title}`}
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
              <Ban className="size-4" />
            </Button>
          ) : null}
        </div>
      </div>

      {/* Failure detail line */}
      {isFailed && job.error_message ? (
        <div className="flex items-start gap-2 border-t border-border px-3 py-2 text-xs text-destructive">
          <AlertCircle className="mt-px size-3.5 shrink-0" aria-hidden />
          <span className="font-mono leading-relaxed">{job.error_message}</span>
        </div>
      ) : null}
    </div>
  );
}
