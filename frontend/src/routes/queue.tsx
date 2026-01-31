import { createFileRoute, Link } from "@tanstack/react-router";
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

export const Route = createFileRoute("/queue")({
  component: QueuePage,
});

const STATUS_LABELS: Record<DownloadStatus, string> = {
  pending: "Pending",
  searching: "Searching...",
  downloading: "Downloading",
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
  converting: "info",
  embedding: "info",
  completed: "success",
  failed: "error",
  cancelled: "warning",
};

function QueuePage() {
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
  } = useQueueStore();

  const pendingCount = getPendingCount();
  const activeCount = getActiveCount();
  const completedCount = getCompletedCount();
  const failedCount = getFailedCount();

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

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
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => (
            <QueueItemCard
              key={item.id}
              item={item}
              index={index}
              onRemove={() => removeItem(item.id)}
              onRetry={() => retryFailed(item.id)}
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
  formatDuration: (seconds: number) => string;
}

function QueueItemCard({
  item,
  index,
  onRemove,
  onRetry,
  formatDuration,
}: QueueItemCardProps) {
  const isActive = ["searching", "downloading", "converting", "embedding"].includes(
    item.status
  );

  return (
    <Card
      variant="bordered"
      hover={!isActive}
      className="animate-slide-up"
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      <CardContent>
        <div className="flex items-center gap-4">
          {/* Track number / Status indicator */}
          <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center shrink-0">
            {isActive ? (
              <div className="equalizer">
                <div className="equalizer-bar" />
                <div className="equalizer-bar" />
                <div className="equalizer-bar" />
              </div>
            ) : (
              <span className="text-sm font-medium text-zinc-500">
                {String(index + 1).padStart(2, "0")}
              </span>
            )}
          </div>

          {/* Song Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className="text-zinc-100 font-medium truncate">
                {item.song.name}
              </h3>
              <Badge variant={STATUS_VARIANTS[item.status]} size="sm">
                {STATUS_LABELS[item.status]}
              </Badge>
            </div>
            <p className="text-sm text-zinc-500 truncate">
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
            {formatDuration(item.song.duration_seconds)}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {item.status === "failed" && (
              <Button size="sm" variant="outline" onClick={onRetry}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retry
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
