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
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { useDevConfig } from "@/contexts/DevConfigContext";
import { useAuthStore } from "@/stores/auth";
import { config } from "@/config";

export const Route = createFileRoute("/queue")({
  beforeLoad: () => {
    if (config.mode === "hosted") {
      throw redirect({
        to: "/",
      });
    }

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
  const isCompleted = item.status === "completed";

  return (
    <div className={`group relative rounded-xl border transition-all ${
      isActive
        ? "bg-zinc-800/60 border-accent-needle/30"
        : isFailed
          ? "bg-red-950/20 border-red-500/20 hover:border-red-500/30"
          : isCompleted
            ? "bg-emerald-950/10 border-emerald-500/20 hover:border-emerald-500/30"
            : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"
    }`}>
      <div className="flex items-start gap-4 p-4">
        {/* Cover Art */}
        <CoverArt
          src={item.song.cover_url ?? null}
          alt={item.song.name}
          size="md"
          fallbackIcon="track"
          className="shrink-0"
        />

        {/* Main Content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Title Row */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <Link
                  to="/song/$id"
                  params={{ id: item.song.platform_id }}
                  className="font-medium text-zinc-100 hover:text-accent-needle transition-colors truncate"
                >
                  {item.song.name}
                </Link>
                <StatusBadge status={item.status} />
              </div>
              <p className="text-sm text-zinc-400 truncate mt-0.5">
                {item.song.artist}
              </p>
            </div>

            {/* Actions - visible on hover */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
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

          {/* Platform Info */}
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-800/80 text-zinc-400">
              <span className="uppercase tracking-wide">{item.song.platform}</span>
              {item.match && (
                <>
                  <svg className="w-3 h-3 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <span className="uppercase tracking-wide">{item.match.target_platform}</span>
                </>
              )}
            </span>
          </div>

          {/* Progress bar for active downloads */}
          {isActive && (
            <div className="flex items-center gap-3 pt-1">
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
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-red-950/30 border border-red-500/20">
              <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-red-300 leading-relaxed">{item.error}</p>
            </div>
          )}
        </div>
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
        <div className="space-y-3">
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
