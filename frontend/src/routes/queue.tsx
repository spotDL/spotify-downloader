import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import {
  useQueueStore,
  type QueueItem,
  type DownloadStatus,
} from "@/stores/queue";
import {
  Button,
  Card,
  CardContent,
  Badge,
  Select,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { useDevConfig } from "@/contexts/DevConfigContext";
import { useAuthStore } from "@/stores/auth";

export const Route = createFileRoute("/queue")({
  beforeLoad: () => {
    const { isAuthenticated } = useAuthStore.getState();
    if (!isAuthenticated) {
      throw redirect({
        to: "/auth/login",
        search: {
          redirect: "/queue",
        },
      });
    }
  },
  component: QueuePage,
});

// ============================================================================
// SIMPLE PROGRESS BAR
// ============================================================================

function ProgressBar({ progress, status }: { progress: number; status: DownloadStatus }) {
  const isActive = ["searching", "downloading", "processing", "converting", "embedding"].includes(status);
  const isComplete = status === "completed";
  const isFailed = status === "failed";

  let barColor = "bg-accent-needle";
  if (isComplete) barColor = "bg-emerald-500";
  if (isFailed) barColor = "bg-red-500";

  return (
    <div className="h-1 w-full bg-zinc-800 rounded-full overflow-hidden">
      <div
        className={`h-full ${barColor} transition-all duration-300 ${isActive ? "animate-pulse" : ""}`}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

// ============================================================================
// STATUS BADGE
// ============================================================================

function StatusBadge({ status }: { status: DownloadStatus }) {
  const statusConfig: Record<DownloadStatus, { label: string; variant: "success" | "warning" | "error" | "info" | "muted" }> = {
    pending: { label: "Pending", variant: "muted" },
    searching: { label: "Searching", variant: "info" },
    downloading: { label: "Downloading", variant: "info" },
    processing: { label: "Processing", variant: "info" },
    converting: { label: "Converting", variant: "info" },
    embedding: { label: "Embedding", variant: "info" },
    completed: { label: "Done", variant: "success" },
    failed: { label: "Failed", variant: "error" },
    cancelled: { label: "Cancelled", variant: "muted" },
  };

  const { label, variant } = statusConfig[status];

  return <Badge variant={variant} size="sm">{label}</Badge>;
}

// ============================================================================
// QUEUE ITEM ROW
// ============================================================================

function QueueItemRow({
  item,
  onRetry,
  onRemove,
}: {
  item: QueueItem;
  onRetry: () => void;
  onRemove: () => void;
}) {
  const isActive = ["searching", "downloading", "processing", "converting", "embedding"].includes(item.status);
  const isFailed = item.status === "failed";

  return (
    <div className={`group flex items-center gap-4 p-4 rounded-xl transition-colors ${
      isActive ? "bg-zinc-800/50" : "hover:bg-zinc-800/30"
    }`}>
      {/* Cover Art */}
      <CoverArt
        src={item.song.cover_url ?? null}
        alt={item.song.name}
        size="md"
        fallbackIcon="track"
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Link
            to="/song/$id"
            params={{ id: item.song.platform_id }}
            className="font-medium text-zinc-100 hover:text-accent-needle transition-colors truncate"
          >
            {item.song.name}
          </Link>
          <StatusBadge status={item.status} />
        </div>

        <p className="text-sm text-zinc-400 truncate mb-2">
          {item.song.artist}
        </p>

        {/* Progress bar for active downloads */}
        {isActive && (
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <ProgressBar progress={item.progress} status={item.status} />
            </div>
            <span className="text-xs text-zinc-500 font-mono w-12 text-right">
              {item.progress}%
            </span>
            {item.speed && (
              <span className="text-xs text-zinc-500">{item.speed}</span>
            )}
          </div>
        )}

        {/* Error message */}
        {isFailed && item.error && (
          <p className="text-xs text-red-400 mt-1">{item.error}</p>
        )}
      </div>

      {/* Platform info */}
      <div className="hidden sm:flex items-center gap-2 text-xs text-zinc-500">
        <span className="uppercase">{item.song.platform}</span>
        {item.match && (
          <>
            <span>→</span>
            <span className="uppercase">{item.match.target_platform}</span>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {isFailed && (
          <button
            onClick={onRetry}
            className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
            title="Retry"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}
        <button
          onClick={onRemove}
          className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-red-400 transition-colors"
          title="Remove"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN QUEUE PAGE
// ============================================================================

function QueuePage() {
  const {
    items,
    removeItem,
    clearCompleted,
    clearAll,
    retryFailed,
    maxConcurrent,
    setMaxConcurrent,
  } = useQueueStore();

  const { features } = useDevConfig();

  const [filter, setFilter] = useState<"all" | "active" | "completed" | "failed">("all");

  // Filter items
  const filteredItems = useMemo(() => {
    switch (filter) {
      case "active":
        return items.filter((item) =>
          ["pending", "searching", "downloading", "processing", "converting", "embedding"].includes(item.status)
        );
      case "completed":
        return items.filter((item) => item.status === "completed");
      case "failed":
        return items.filter((item) => item.status === "failed" || item.status === "cancelled");
      default:
        return items;
    }
  }, [items, filter]);

  // Stats
  const stats = useMemo(() => {
    const pending = items.filter((i) => i.status === "pending").length;
    const active = items.filter((i) =>
      ["searching", "downloading", "processing", "converting", "embedding"].includes(i.status)
    ).length;
    const completed = items.filter((i) => i.status === "completed").length;
    const failed = items.filter((i) => i.status === "failed" || i.status === "cancelled").length;
    return { pending, active, completed, failed, total: items.length };
  }, [items]);

  // Overall progress
  const overallProgress = useMemo(() => {
    if (items.length === 0) return 0;
    const total = items.reduce((acc, item) => acc + item.progress, 0);
    return Math.round(total / items.length);
  }, [items]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Download Queue</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {stats.total === 0
              ? "No downloads"
              : `${stats.total} ${stats.total === 1 ? "track" : "tracks"} in queue`}
          </p>
        </div>

        {stats.total > 0 && (
          <div className="flex items-center gap-4">
            {/* Concurrent downloads */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-zinc-400">Threads</span>
              <Select
                options={[
                  { value: "1", label: "1" },
                  { value: "2", label: "2" },
                  { value: "3", label: "3" },
                  { value: "4", label: "4" },
                  { value: "5", label: "5" },
                ]}
                value={String(maxConcurrent)}
                onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                className="w-16"
              />
            </div>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats.total > 0 && (
        <div className="flex items-center gap-6 text-sm">
          <button
            onClick={() => setFilter("all")}
            className={`transition-colors ${filter === "all" ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            All ({stats.total})
          </button>
          <button
            onClick={() => setFilter("active")}
            className={`transition-colors ${filter === "active" ? "text-accent-needle" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            Active ({stats.pending + stats.active})
          </button>
          <button
            onClick={() => setFilter("completed")}
            className={`transition-colors ${filter === "completed" ? "text-emerald-400" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            Done ({stats.completed})
          </button>
          <button
            onClick={() => setFilter("failed")}
            className={`transition-colors ${filter === "failed" ? "text-red-400" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            Failed ({stats.failed})
          </button>

          <div className="flex-1" />

          {/* Actions */}
          {stats.completed > 0 && (
            <Button variant="ghost" size="sm" onClick={clearCompleted}>
              Clear done
            </Button>
          )}
          {stats.total > 0 && (
            <Button variant="ghost" size="sm" onClick={clearAll} className="text-zinc-500 hover:text-red-400">
              Clear all
            </Button>
          )}
        </div>
      )}

      {/* Overall Progress */}
      {(stats.active > 0 || stats.pending > 0) && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-400">Overall progress</span>
            <span className="text-zinc-300 font-medium">{overallProgress}%</span>
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-needle transition-all duration-300"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Queue List */}
      {filteredItems.length > 0 ? (
        <div className="space-y-2">
          {filteredItems.map((item) => (
            <QueueItemRow
              key={item.id}
              item={item}
              onRetry={() => retryFailed(item.id)}
              onRemove={() => removeItem(item.id)}
            />
          ))}
        </div>
      ) : (
        <Card variant="bordered">
          <CardContent className="py-16 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800 flex items-center justify-center">
              <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-zinc-300 mb-2">
              {filter === "all" ? "Queue is empty" : `No ${filter} downloads`}
            </h3>
            <p className="text-zinc-500 mb-4">
              {filter === "all"
                ? "Search for songs and add them to your queue"
                : "Try a different filter"}
            </p>
            {filter === "all" && (
              <Link to="/search">
                <Button variant="primary">Search Music</Button>
              </Link>
            )}
          </CardContent>
        </Card>
      )}

      {/* Download location notice */}
      {features.canDownload && stats.completed > 0 && (
        <p className="text-xs text-zinc-500 text-center">
          Downloads saved to your configured output directory
        </p>
      )}
    </div>
  );
}
