import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
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
import { features, config } from "@/config";
import type { DisplayEntityType } from "@/types";

export const Route = createFileRoute("/queue")({
  component: QueuePage,
});

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

  // Check if we have any grouped items
  const hasEntityGroups = Array.from(entityGroups.keys()).some((key) => key !== "individual");

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
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center">
              <svg className="w-10 h-10 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-50">Download Queue</h1>
          <p className="text-zinc-400 mt-1">Monitor and manage your downloads</p>
        </div>
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

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Pending"
          value={pendingCount}
          color="zinc"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          label="Active"
          value={activeCount}
          color="sky"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          }
          animated
        />
        <StatCard
          label="Completed"
          value={completedCount}
          color="emerald"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          label="Failed"
          value={failedCount}
          color="red"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Actions */}
      {items.length > 0 && (
        <div className="flex gap-3">
          {completedCount > 0 && (
            <Button variant="outline" size="sm" onClick={clearCompleted}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Clear Completed
            </Button>
          )}
          {failedCount > 0 && (
            <Button variant="outline" size="sm" onClick={clearFailed}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Clear Failed
            </Button>
          )}
          <Button variant="danger" size="sm" onClick={clearAll}>
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear All
          </Button>
        </div>
      )}

      {/* View Toggle */}
      {hasEntityGroups && items.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-500">View:</span>
          <button
            onClick={() => setShowGrouped(true)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              showGrouped
                ? "bg-emerald-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            Grouped
          </button>
          <button
            onClick={() => setShowGrouped(false)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              !showGrouped
                ? "bg-emerald-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            List
          </button>
        </div>
      )}

      {/* Queue Items */}
      {items.length === 0 ? (
        <Card variant="bordered" className="py-16">
          <CardContent className="text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-zinc-800/50 flex items-center justify-center">
              <svg className="w-10 h-10 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <p className="text-lg text-zinc-300 font-medium">No downloads in queue</p>
            <p className="text-sm text-zinc-500 mt-2">
              <Link to="/" className="text-emerald-400 hover:text-emerald-300 transition-colors">
                Search for a song
              </Link>{" "}
              to start downloading
            </p>
          </CardContent>
        </Card>
      ) : showGrouped && hasEntityGroups ? (
        <div className="space-y-6">
          {Array.from(entityGroups.entries()).map(([key, groupItems]) => {
            const entityContext = groupItems[0]?.entityContext;
            const isIndividual = key === "individual";

            if (isIndividual) {
              return (
                <div key={key} className="space-y-3">
                  <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-wider">
                    Individual Downloads
                  </h3>
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
        <div className="space-y-3">
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

interface StatCardProps {
  label: string;
  value: number;
  color: "zinc" | "sky" | "emerald" | "red";
  icon: React.ReactNode;
  animated?: boolean;
}

function StatCard({ label, value, color, icon, animated }: StatCardProps) {
  const colorClasses = {
    zinc: "from-zinc-500/20 to-zinc-600/20 text-zinc-400",
    sky: "from-sky-500/20 to-sky-600/20 text-sky-400",
    emerald: "from-emerald-500/20 to-emerald-600/20 text-emerald-400",
    red: "from-red-500/20 to-red-600/20 text-red-400",
  };

  const valueColors = {
    zinc: "text-zinc-100",
    sky: "text-sky-400",
    emerald: "text-emerald-400",
    red: "text-red-400",
  };

  return (
    <Card variant="bordered" className="relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-br ${colorClasses[color]} opacity-50`} />
      <CardContent className="relative py-4">
        <div className="flex items-center justify-between">
          <div>
            <p className={`text-3xl font-bold ${valueColors[color]}`}>
              {value}
            </p>
            <p className="text-sm text-zinc-400 mt-1">{label}</p>
          </div>
          <div className={`${colorClasses[color]} ${animated ? "animate-pulse" : ""}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

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

  return (
    <Card
      variant="bordered"
      hover={!isActive}
      className={`animate-slide-up ${compact ? "py-1" : ""}`}
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      <CardContent className={compact ? "py-2" : undefined}>
        <div className="flex items-center gap-4">
          {/* Track number / Status indicator */}
          <div className={`${compact ? "w-8 h-8" : "w-10 h-10"} rounded-xl bg-zinc-800 flex items-center justify-center shrink-0`}>
            {isActive ? (
              <div className="equalizer">
                <div className="equalizer-bar" />
                <div className="equalizer-bar" />
                <div className="equalizer-bar" />
              </div>
            ) : (
              <span className={`${compact ? "text-xs" : "text-sm"} font-medium text-zinc-500`}>
                {item.entityContext?.position || String(index + 1).padStart(2, "0")}
              </span>
            )}
          </div>

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

            {/* Progress Bar */}
            {isActive && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-zinc-500 mb-1.5">
                  <span className="font-medium">{item.progress}%</span>
                  <span>
                    {item.speed && `${item.speed} • `}
                    {item.eta && `ETA: ${item.eta}`}
                  </span>
                </div>
                <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full progress-gradient rounded-full transition-all duration-300"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error Message */}
            {item.status === "failed" && item.error && (
              <p className="text-sm text-red-400 mt-2 flex items-center gap-1.5">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {item.error}
              </p>
            )}
          </div>

          {/* Duration */}
          <div className="text-sm text-zinc-500 tabular-nums">
            {formatDuration(item.song.duration)}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {item.status === "completed" && (
              <Button size="sm" variant="primary" onClick={onDownloadFile}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Save
              </Button>
            )}
            {item.status === "failed" && (
              <Button size="sm" variant="outline" onClick={onRetry}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retry
              </Button>
            )}
            {isActive && (
              <Button size="sm" variant="danger" onClick={onCancel}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Cancel
              </Button>
            )}
            {!isActive && (
              <Button size="sm" variant="ghost" onClick={onRemove} className="text-zinc-400 hover:text-red-400">
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

// Entity type icons
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
  const completedCount = items.filter((i) => i.status === "completed").length;
  const failedCount = items.filter((i) => i.status === "failed").length;
  const activeCount = items.filter((i) =>
    ["searching", "downloading", "processing", "converting", "embedding"].includes(i.status)
  ).length;
  const total = entityContext.total;
  const progress = Math.round((completedCount / total) * 100);

  return (
    <div className="space-y-3">
      {/* Entity Header */}
      <div className="p-4 bg-gradient-to-r from-zinc-900/80 via-zinc-900/60 to-zinc-900/80 rounded-xl border border-zinc-800/50">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center text-white">
              {entityTypeIcons[entityContext.type]}
            </div>
            <div>
              <h3 className="font-semibold text-zinc-100">{entityContext.name}</h3>
              <p className="text-sm text-zinc-500 capitalize">
                {entityContext.type} - {total} tracks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Progress indicator */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
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
              <div className="w-24 h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full progress-gradient rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-sm text-zinc-400 tabular-nums">{progress}%</span>
            </div>

            <a
              href={entityContext.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      {/* Entity Items */}
      <div className="space-y-2 pl-4 border-l-2 border-zinc-800">
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
  );
}
