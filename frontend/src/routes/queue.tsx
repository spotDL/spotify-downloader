import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import {
  useQueueStore,
  type QueueItem,
  type DownloadStatus,
  type EntityContext,
} from "@/stores/queue";
import {
  Button,
  Card,
  CardContent,
  Badge,
  Select,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { EqualizerLoader } from "@/components/ui";
import { StatCard, StatCardGrid } from "@/components/ui/stat-card";
import { features, config } from "@/config";
import type { DisplayEntityType } from "@/types";

export const Route = createFileRoute("/queue")({
  component: QueuePage,
});

// ============================================================================
// STATUS CONFIGURATION
// ============================================================================

const STATUS_LABELS: Record<DownloadStatus, string> = {
  pending: "Pending",
  searching: "Searching...",
  downloading: "Downloading",
  processing: "Processing",
  converting: "Converting",
  embedding: "Embedding",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const STATUS_VARIANTS: Record<DownloadStatus, "default" | "success" | "warning" | "error" | "info"> = {
  pending: "default",
  searching: "info",
  downloading: "info",
  processing: "info",
  converting: "info",
  embedding: "info",
  completed: "success",
  failed: "error",
  cancelled: "warning",
};

// Status icons for better visual hierarchy
const STATUS_ICONS: Partial<Record<DownloadStatus, React.ReactNode>> = {
  completed: (
    <svg className="w-4 h-4 text-accent-safe" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  failed: (
    <svg className="w-4 h-4 text-accent-peak" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  cancelled: (
    <svg className="w-4 h-4 text-accent-warm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
    </svg>
  ),
};

// ============================================================================
// MAIN QUEUE PAGE
// ============================================================================

function QueuePage() {
  const [showGrouped, setShowGrouped] = useState(true);
  const {
    items,
    maxConcurrent,
    removeItem,
    clearCompleted,
    clearFailed,
    clearAll,
    retryFailed,
    setMaxConcurrent,
    getPendingCount,
    getActiveCount,
    getCompletedCount,
    getFailedCount,
    getEntityGroups,
    cancelDownload,
    downloadFile,
  } = useQueueStore();

  const pendingCount = getPendingCount();
  const activeCount = getActiveCount();
  const completedCount = getCompletedCount();
  const failedCount = getFailedCount();
  const entityGroups = getEntityGroups();

  const hasEntityGroups = Array.from(entityGroups.keys()).some((key) => key !== "individual");

  // Calculate total progress for active downloads
  const totalProgress = useMemo(() => {
    const activeItems = items.filter((i) =>
      ["searching", "downloading", "processing", "converting", "embedding"].includes(i.status)
    );
    if (activeItems.length === 0) return 0;
    return Math.round(activeItems.reduce((sum, i) => sum + i.progress, 0) / activeItems.length);
  }, [items]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Show hosted mode message if downloads are disabled
  if (!features.canDownload) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Card variant="bordered" className="max-w-lg w-full animate-scale-in">
          <CardContent className="py-12 text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent-needle/20 to-accent-cool/20 flex items-center justify-center">
              <svg className="w-10 h-10 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-zinc-50 mb-3">
              Download Locally
            </h2>
            <p className="text-zinc-400 mb-6">
              This is the SpotDL Matching Service - a crowdsourced database of verified matches.
              To download songs, self-host SpotDL and connect to this service for the best matches.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a
                href={config.githubUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="primary">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                  Self-Host SpotDL
                </Button>
              </a>
              <Link to="/">
                <Button variant="outline">
                  Back to Search
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Header with overall progress */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-50">Download Queue</h1>
          <p className="text-zinc-400 mt-1">
            {items.length === 0
              ? "No downloads in progress"
              : `${items.length} ${items.length === 1 ? "item" : "items"} in queue`}
          </p>
        </div>

        {/* Overall progress indicator when downloads are active */}
        {activeCount > 0 && (
          <div className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-xl bg-bg-panel border border-zinc-800">
            <EqualizerLoader />
            <div className="text-right">
              <div className="text-sm font-medium text-zinc-200">{totalProgress}%</div>
              <div className="text-xs text-zinc-500">{activeCount} active</div>
            </div>
          </div>
        )}

        <Select
          options={[1, 2, 3, 4, 5, 6, 8, 10, 12, 16].map((n) => ({
            value: String(n),
            label: `${n} concurrent`,
          }))}
          value={String(maxConcurrent)}
          onChange={(e) => setMaxConcurrent(Number(e.target.value))}
          className="w-44"
        />
      </div>

      {/* Stats Grid with improved spacing */}
      <StatCardGrid columns={4}>
        <StatCard
          label="Pending"
          value={pendingCount}
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          variant="default"
        />
        <StatCard
          label="Active"
          value={activeCount}
          icon={<EqualizerLoader />}
          variant="info"
        />
        <StatCard
          label="Completed"
          value={completedCount}
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          variant="success"
        />
        <StatCard
          label="Failed"
          value={failedCount}
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          variant="error"
        />
      </StatCardGrid>

      {/* Actions - Better spacing and grouping */}
      {items.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-bg-panel/50 border border-zinc-800/50">
          <span className="text-sm text-zinc-500 mr-2">Actions:</span>
          {completedCount > 0 && (
            <Button variant="outline" size="sm" onClick={clearCompleted}>
              <svg className="w-4 h-4 mr-2 text-accent-safe" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Clear Completed ({completedCount})
            </Button>
          )}
          {failedCount > 0 && (
            <>
              <Button variant="outline" size="sm" onClick={() => {
                // Retry all failed items
                items.filter(i => i.status === "failed").forEach(i => retryFailed(i.id));
              }}>
                <svg className="w-4 h-4 mr-2 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retry Failed ({failedCount})
              </Button>
              <Button variant="outline" size="sm" onClick={clearFailed}>
                <svg className="w-4 h-4 mr-2 text-accent-peak" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Clear Failed
              </Button>
            </>
          )}
          <div className="flex-1" />
          <Button variant="ghost" size="sm" onClick={clearAll} className="text-zinc-500 hover:text-accent-peak">
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear All
          </Button>
        </div>
      )}

      {/* View Toggle - Improved styling */}
      {hasEntityGroups && items.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-500">View:</span>
          <div className="flex rounded-lg bg-bg-panel border border-zinc-800 p-0.5">
            <button
              onClick={() => setShowGrouped(true)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                showGrouped
                  ? "bg-accent-needle text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Grouped
            </button>
            <button
              onClick={() => setShowGrouped(false)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                !showGrouped
                  ? "bg-accent-needle text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              List
            </button>
          </div>
        </div>
      )}

      {/* Queue Items */}
      {items.length === 0 ? (
        <Card variant="bordered" className="py-16">
          <CardContent className="text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-bg-panel to-bg-surface flex items-center justify-center">
              <svg className="w-10 h-10 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <p className="text-xl text-zinc-300 font-medium">No downloads in queue</p>
            <p className="text-sm text-zinc-500 mt-2 mb-6">
              Search for a song and add it to your download queue
            </p>
            <Link to="/">
              <Button variant="primary">
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Start Searching
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : showGrouped && hasEntityGroups ? (
        <div className="space-y-8">
          {Array.from(entityGroups.entries()).map(([key, groupItems]) => {
            const entityContext = groupItems[0]?.entityContext;
            const isIndividual = key === "individual";

            if (isIndividual) {
              return (
                <div key={key} className="space-y-3">
                  <div className="flex items-center gap-2 px-1">
                    <div className="w-1 h-5 rounded-full bg-zinc-600" />
                    <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
                      Individual Downloads
                    </h3>
                    <Badge variant="muted" size="sm">{groupItems.length}</Badge>
                  </div>
                  <div className="space-y-2">
                    {groupItems.map((item, index) => (
                      <QueueItemCard
                        key={item.id}
                        item={item}
                        index={index}
                        onRemove={() => removeItem(item.id)}
                        onRetry={() => retryFailed(item.id)}
                        onCancel={() => cancelDownload(item.id)}
                        onDownloadFile={() => downloadFile(item.id)}
                        formatDuration={formatDuration}
                      />
                    ))}
                  </div>
                </div>
              );
            }

            return (
              <EntityGroup
                key={key}
                entityContext={entityContext!}
                items={groupItems}
                onRemove={(id) => removeItem(id)}
                onRetry={(id) => retryFailed(id)}
                onCancel={(id) => cancelDownload(id)}
                onDownloadFile={(id) => downloadFile(id)}
                formatDuration={formatDuration}
              />
            );
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, index) => (
            <QueueItemCard
              key={item.id}
              item={item}
              index={index}
              onRemove={() => removeItem(item.id)}
              onRetry={() => retryFailed(item.id)}
              onCancel={() => cancelDownload(item.id)}
              onDownloadFile={() => downloadFile(item.id)}
              formatDuration={formatDuration}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// QUEUE ITEM CARD
// ============================================================================

interface QueueItemCardProps {
  item: QueueItem;
  index: number;
  onRemove: () => void;
  onRetry: () => void;
  onCancel: () => void;
  onDownloadFile: () => void;
  formatDuration: (seconds: number) => string;
  compact?: boolean;
}

function QueueItemCard({
  item,
  index,
  onRemove,
  onRetry,
  onCancel,
  onDownloadFile,
  formatDuration,
  compact = false,
}: QueueItemCardProps) {
  const isActive = ["searching", "downloading", "processing", "converting", "embedding"].includes(
    item.status
  );
  const isCompleted = item.status === "completed";
  const isFailed = item.status === "failed";

  return (
    <Card
      variant="bordered"
      hover={!isActive}
      className={`
        transition-all duration-300 ease-out
        ${compact ? "" : ""}
        ${isActive ? "border-accent-needle/30 bg-accent-needle/5" : ""}
        ${isCompleted ? "border-accent-safe/20" : ""}
        ${isFailed ? "border-accent-peak/20" : ""}
      `}
      style={{
        animationDelay: `${index * 0.02}s`,
        animationFillMode: "backwards",
      }}
    >
      <CardContent className={compact ? "py-3" : undefined}>
        <div className="flex items-center gap-4">
          {/* Track number / Status indicator */}
          <div className={`${compact ? "w-8 h-8" : "w-10 h-10"} rounded-xl bg-bg-panel flex items-center justify-center shrink-0 transition-colors duration-300`}>
            {isActive ? (
              <EqualizerLoader />
            ) : STATUS_ICONS[item.status] ? (
              STATUS_ICONS[item.status]
            ) : (
              <span className={`${compact ? "text-xs" : "text-sm"} font-mono text-zinc-500`}>
                {item.entityContext?.position || String(index + 1).padStart(2, "0")}
              </span>
            )}
          </div>

          {/* Cover Art */}
          {!compact && (
            <CoverArt
              src={item.song.cover_url ?? null}
              alt={item.song.name}
              size="xs"
            />
          )}

          {/* Song Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className={`text-zinc-100 font-medium truncate ${compact ? "text-sm" : ""}`}>
                {item.song.name}
              </h3>
              <Badge variant={STATUS_VARIANTS[item.status]} size="sm">
                {STATUS_LABELS[item.status]}
              </Badge>
            </div>
            <p className={`${compact ? "text-xs" : "text-sm"} text-zinc-500 truncate`}>
              {item.song.artists.join(", ")}
            </p>

            {/* Progress Bar - Smoother animation */}
            {isActive && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-zinc-500 mb-1.5">
                  <span className="font-medium font-mono">{item.progress}%</span>
                  <span>
                    {item.speed && `${item.speed} | `}
                    {item.eta && `ETA: ${item.eta}`}
                  </span>
                </div>
                <div className="h-1.5 bg-bg-panel rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${item.progress}%`,
                      background: `linear-gradient(90deg, var(--accent-safe) 0%, var(--accent-needle) ${Math.min(100, item.progress + 20)}%, var(--accent-peak) 100%)`,
                    }}
                  />
                </div>
              </div>
            )}

            {/* Error Message - Better visibility */}
            {item.status === "failed" && item.error && (
              <div className="mt-2 p-2 rounded-lg bg-accent-peak/10 border border-accent-peak/20">
                <p className="text-sm text-accent-peak flex items-start gap-1.5">
                  <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{item.error}</span>
                </p>
              </div>
            )}
          </div>

          {/* Duration */}
          <div className="text-sm font-mono text-zinc-500 hidden sm:block">
            {formatDuration(item.song.duration)}
          </div>

          {/* Actions - Better organized */}
          <div className="flex items-center gap-2">
            {item.status === "completed" && (
              <Button size="sm" variant="primary" onClick={onDownloadFile} className="gap-1.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Save
              </Button>
            )}
            {item.status === "failed" && (
              <Button size="sm" variant="outline" onClick={onRetry} className="gap-1.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retry
              </Button>
            )}
            {isActive && (
              <Button size="sm" variant="ghost" onClick={onCancel} className="text-accent-peak hover:text-accent-peak hover:bg-accent-peak/10">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            )}
            {!isActive && (
              <Button size="sm" variant="ghost" onClick={onRemove} className="text-zinc-400 hover:text-accent-peak hover:bg-accent-peak/10">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// ENTITY TYPE ICONS
// ============================================================================

const entityTypeIcons: Record<DisplayEntityType, React.ReactNode> = {
  artist: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  ),
  album: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
  playlist: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  ),
  track: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
};

// ============================================================================
// ENTITY GROUP
// ============================================================================

interface EntityGroupProps {
  entityContext: EntityContext;
  items: QueueItem[];
  onRemove: (id: string) => void;
  onRetry: (id: string) => void;
  onCancel: (id: string) => void;
  onDownloadFile: (id: string) => void;
  formatDuration: (seconds: number) => string;
}

function EntityGroup({
  entityContext,
  items,
  onRemove,
  onRetry,
  onCancel,
  onDownloadFile,
  formatDuration,
}: EntityGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const completedCount = items.filter((i) => i.status === "completed").length;
  const failedCount = items.filter((i) => i.status === "failed").length;
  const activeCount = items.filter((i) =>
    ["searching", "downloading", "processing", "converting", "embedding"].includes(i.status)
  ).length;
  const total = entityContext.total;
  const progress = Math.round((completedCount / total) * 100);

  return (
    <div className="space-y-3">
      {/* Entity Header - Clickable to expand/collapse */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 bg-gradient-to-r from-bg-panel via-bg-panel/90 to-bg-panel rounded-xl border border-zinc-800/50 hover:border-zinc-700 transition-all"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-needle to-accent-cool flex items-center justify-center text-white shadow-lg shadow-accent-needle/20">
              {entityTypeIcons[entityContext.type]}
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-zinc-100">{entityContext.name}</h3>
              <p className="text-sm text-zinc-500 capitalize">
                {entityContext.type} | {total} tracks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Status badges */}
            <div className="hidden sm:flex items-center gap-1.5">
              {completedCount > 0 && (
                <Badge variant="success" size="sm">
                  {completedCount} done
                </Badge>
              )}
              {activeCount > 0 && (
                <Badge variant="info" size="sm">
                  {activeCount} active
                </Badge>
              )}
              {failedCount > 0 && (
                <Badge variant="error" size="sm">
                  {failedCount} failed
                </Badge>
              )}
            </div>

            {/* Progress bar */}
            <div className="flex items-center gap-3">
              <div className="w-24 h-2 bg-bg-chassis rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${progress}%`,
                    background: `linear-gradient(90deg, var(--accent-safe) 0%, var(--accent-needle) 100%)`,
                  }}
                />
              </div>
              <span className="text-sm font-mono text-zinc-400 w-10">{progress}%</span>
            </div>

            {/* Expand/collapse indicator */}
            <svg
              className={`w-5 h-5 text-zinc-500 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </button>

      {/* Entity Items - Collapsible with smooth animation */}
      <div
        className={`transition-all duration-300 ease-out overflow-hidden ${
          isExpanded ? "opacity-100" : "opacity-0 max-h-0"
        }`}
        style={{ maxHeight: isExpanded ? `${items.length * 100}px` : 0 }}
      >
        <div className="space-y-2 pl-4 border-l-2 border-zinc-800 ml-6">
          {items.map((item, index) => (
            <QueueItemCard
              key={item.id}
              item={item}
              index={index}
              onRemove={() => onRemove(item.id)}
              onRetry={() => onRetry(item.id)}
              onCancel={() => onCancel(item.id)}
              onDownloadFile={() => onDownloadFile(item.id)}
              formatDuration={formatDuration}
              compact
            />
          ))}
        </div>
      </div>
    </div>
  );
}
