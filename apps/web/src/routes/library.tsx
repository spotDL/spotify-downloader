import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import type { DownloadJobOut } from "../api/generated/types.gen";
import {
  batchSaveFileUrl,
  downloadFileUrl,
  useDownloads,
} from "../api/downloads";
import { useFeature } from "../app/config";
import { joinArtists } from "../lib/format";
import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { toast } from "../components/Toasts";
import { DownloadIcon, LibraryIcon, NoteIcon } from "../components/icons";

export const Route = createFileRoute("/library")({ component: LibraryPage });

function LibraryPage() {
  if (!useFeature("library")) {
    return (
      <div className="mx-auto w-full max-w-[1080px] px-6 py-16">
        <EmptyState
          title="Library"
          description="The library is not available on this server."
        />
      </div>
    );
  }
  return <LibraryBrowser />;
}

// A completed batch: id, its jobs (files), and a representative date.
type Batch = { key: string; batchId: string | null; jobs: DownloadJobOut[] };

function groupByBatch(jobs: DownloadJobOut[]): Batch[] {
  const order: string[] = [];
  const groups = new Map<string, Batch>();
  for (const job of jobs) {
    const key = job.batch_id ?? `job:${job.id}`;
    let group = groups.get(key);
    if (!group) {
      group = { key, batchId: job.batch_id, jobs: [] };
      groups.set(key, group);
      order.push(key);
    }
    group.jobs.push(job);
  }
  return order.map((key) => groups.get(key)!);
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
}

function LibraryBrowser() {
  // The library is the completed-jobs view (`status=completed`), grouped by
  // batch with per-file download links and a per-batch `.spotdl` save file.
  const query = useDownloads({ status: "completed", limit: 100 });

  if (query.isPending) {
    return (
      <div className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 py-7">
        <Header />
        <div className="flex justify-center py-16">
          <Spinner label="Loading your library" className="size-8" />
        </div>
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 py-7">
        <Header />
        <ErrorState
          description="Couldn't load your library."
          action={
            <Button variant="secondary" onClick={() => void query.refetch()}>
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  if (query.data.jobs.length === 0) {
    return (
      <div className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 py-7">
        <Header />
        <EmptyState
          title="Nothing downloaded yet"
          description="Completed downloads show up here with file links and a saved playlist file."
        />
      </div>
    );
  }

  return <LibraryContent jobs={query.data.jobs} />;
}

function Header() {
  return (
    <div className="flex flex-col gap-1">
      <h1 className="text-2xl font-bold tracking-tight text-fg">Library</h1>
      <p className="text-sm text-muted">
        Completed downloads, grouped by the batch that produced them.
      </p>
    </div>
  );
}

function LibraryContent({ jobs }: { jobs: DownloadJobOut[] }) {
  const batches = useMemo(() => groupByBatch(jobs), [jobs]);
  const [selectedKey, setSelectedKey] = useState<string>(batches[0].key);
  const selected =
    batches.find((b) => b.key === selectedKey) ?? batches[0];

  return (
    <div className="mx-auto flex w-full max-w-[1080px] flex-col gap-6 px-6 py-7">
      <Header />
      <div className="grid gap-5 md:grid-cols-[300px_1fr]">
        <BatchList
          batches={batches}
          selectedKey={selected.key}
          onSelect={setSelectedKey}
        />
        <BatchFiles batch={selected} />
      </div>
    </div>
  );
}

function BatchList({
  batches,
  selectedKey,
  onSelect,
}: {
  batches: Batch[];
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  return (
    <nav
      aria-label="Downloaded batches"
      className="flex flex-col gap-1.5 rounded-card border border-line-soft bg-surface p-2"
    >
      {batches.map((batch) => {
        const active = batch.key === selectedKey;
        const first = batch.jobs[0];
        const title = `${batch.jobs.length} ${
          batch.jobs.length === 1 ? "track" : "tracks"
        }`;
        return (
          <button
            key={batch.key}
            type="button"
            aria-current={active}
            onClick={() => onSelect(batch.key)}
            className={`flex items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald ${
              active ? "bg-elevated" : "hover:bg-elevated/60"
            }`}
          >
            <span
              className={`grid size-9 shrink-0 place-items-center rounded-lg ring-1 ring-white/5 ${
                active ? "bg-emerald/15 text-emerald" : "bg-panel text-muted"
              }`}
            >
              <LibraryIcon className="size-4" />
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-[13px] font-medium text-fg">
                {title}
              </span>
              <span className="truncate font-mono text-[11px] text-muted tabular-nums">
                {formatDate(first.created_at)}
                {batch.batchId ? ` · #${batch.batchId.slice(0, 6)}` : ""}
              </span>
            </span>
            <Badge tone={active ? "brand" : "muted"}>{batch.jobs.length}</Badge>
          </button>
        );
      })}
    </nav>
  );
}

function BatchFiles({ batch }: { batch: Batch }) {
  const first = batch.jobs[0];
  return (
    <section className="flex flex-col gap-4 rounded-card border border-line-soft bg-surface px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col">
          <h2 className="text-[15px] font-bold tracking-tight text-fg">
            {batch.jobs.length} {batch.jobs.length === 1 ? "file" : "files"}
          </h2>
          <span className="font-mono text-[11px] text-muted tabular-nums">
            {formatDate(first.created_at)}
            {batch.batchId ? ` · #${batch.batchId.slice(0, 8)}` : ""}
          </span>
        </div>
        {batch.batchId ? (
          <a
            href={batchSaveFileUrl(batch.batchId)}
            className="inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs font-semibold text-ink-2 transition-colors hover:bg-elevated hover:text-fg"
          >
            <DownloadIcon className="size-3.5" />
            Save file (.spotdl)
          </a>
        ) : null}
      </div>

      <ul className="flex flex-col divide-y divide-line-soft">
        {batch.jobs.map((job) => (
          <FileRow key={job.id} job={job} />
        ))}
      </ul>
    </section>
  );
}

function FileRow({ job }: { job: DownloadJobOut }) {
  // DownloadJobOut exposes no file size, so only path + format are shown.
  const path = job.output_path;

  const copyPath = () => {
    if (path == null) return;
    void navigator.clipboard
      ?.writeText(path)
      .then(() => toast.info("Copied the file path."))
      .catch(() => toast.error("Couldn't copy the path."));
  };

  return (
    <li className="group flex items-center gap-3 py-2.5">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-elevated text-muted ring-1 ring-white/5">
        <NoteIcon className="size-4" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate text-[13px] font-medium text-fg">
          {job.track_name ?? "Unknown track"}
        </span>
        <span className="truncate text-[11px] text-muted">
          {job.artists.length > 0 ? joinArtists(job.artists) : "—"}
        </span>
        {path ? (
          <span className="truncate font-mono text-[11px] text-ink-4">
            {path}
          </span>
        ) : null}
      </div>

      {job.output_format ? (
        <Badge tone="muted" className="uppercase">
          {job.output_format}
        </Badge>
      ) : null}

      <div className="flex items-center gap-1.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        {path ? (
          <button
            type="button"
            onClick={copyPath}
            className="rounded-md px-2 py-1 text-xs font-semibold text-ink-2 hover:bg-elevated hover:text-fg"
          >
            Copy path
          </button>
        ) : null}
        {job.skip_reason == null && path != null ? (
          <a
            href={downloadFileUrl(job.id)}
            download
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-emerald hover:bg-elevated"
          >
            <DownloadIcon className="size-3.5" />
            Download
          </a>
        ) : null}
      </div>
    </li>
  );
}
