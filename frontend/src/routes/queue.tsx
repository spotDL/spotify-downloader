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
  embedding: "Embedding metadata",
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Download Queue</h1>
        <div className="flex items-center gap-2">
          <Select
            options={[1, 2, 3, 4, 5, 6, 8, 10, 12, 16].map((n) => ({
              value: String(n),
              label: `${n} concurrent`,
            }))}
            value={String(maxConcurrent)}
            onChange={(e) => setMaxConcurrent(Number(e.target.value))}
            className="w-40"
          />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card variant="bordered">
          <CardContent className="text-center py-4">
            <p className="text-2xl font-bold text-gray-100">{pendingCount}</p>
            <p className="text-sm text-gray-400">Pending</p>
          </CardContent>
        </Card>
        <Card variant="bordered">
          <CardContent className="text-center py-4">
            <p className="text-2xl font-bold text-blue-400">{activeCount}</p>
            <p className="text-sm text-gray-400">Active</p>
          </CardContent>
        </Card>
        <Card variant="bordered">
          <CardContent className="text-center py-4">
            <p className="text-2xl font-bold text-green-400">{completedCount}</p>
            <p className="text-sm text-gray-400">Completed</p>
          </CardContent>
        </Card>
        <Card variant="bordered">
          <CardContent className="text-center py-4">
            <p className="text-2xl font-bold text-red-400">{failedCount}</p>
            <p className="text-sm text-gray-400">Failed</p>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      {items.length > 0 && (
        <div className="flex gap-2">
          {completedCount > 0 && (
            <Button variant="outline" size="sm" onClick={clearCompleted}>
              Clear Completed
            </Button>
          )}
          {failedCount > 0 && (
            <Button variant="outline" size="sm" onClick={clearFailed}>
              Clear Failed
            </Button>
          )}
          <Button variant="danger" size="sm" onClick={clearAll}>
            Clear All
          </Button>
        </div>
      )}

      {/* Queue Items */}
      {items.length === 0 ? (
        <Card variant="bordered">
          <CardContent className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-700 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-gray-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            </div>
            <p className="text-gray-400">No downloads in queue</p>
            <p className="text-sm text-gray-500 mt-2">
              <Link to="/" className="text-blue-400 hover:text-blue-300">
                Search for a song
              </Link>{" "}
              to start downloading
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <QueueItemCard
              key={item.id}
              item={item}
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

interface QueueItemCardProps {
  item: QueueItem;
  onRemove: () => void;
  onRetry: () => void;
  formatDuration: (seconds: number) => string;
}

function QueueItemCard({
  item,
  onRemove,
  onRetry,
  formatDuration,
}: QueueItemCardProps) {
  const isActive = ["searching", "downloading", "converting", "embedding"].includes(
    item.status
  );

  return (
    <Card variant="bordered" className="hover:border-gray-600 transition-colors">
      <CardContent>
        <div className="flex items-center gap-4">
          {/* Song Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-gray-100 font-medium truncate">
                {item.song.name}
              </h3>
              <Badge variant={STATUS_VARIANTS[item.status]}>
                {STATUS_LABELS[item.status]}
              </Badge>
            </div>
            <p className="text-sm text-gray-400 truncate">
              {item.song.artists.join(", ")}
            </p>

            {/* Progress Bar */}
            {isActive && (
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>{item.progress}%</span>
                  <span>
                    {item.speed && `${item.speed} • `}
                    {item.eta && `ETA: ${item.eta}`}
                  </span>
                </div>
                <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error Message */}
            {item.status === "failed" && item.error && (
              <p className="text-sm text-red-400 mt-1">{item.error}</p>
            )}
          </div>

          {/* Duration */}
          <div className="text-sm text-gray-500">
            {formatDuration(item.song.duration_seconds)}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {item.status === "failed" && (
              <Button size="sm" variant="outline" onClick={onRetry}>
                Retry
              </Button>
            )}
            {!isActive && (
              <Button size="sm" variant="ghost" onClick={onRemove}>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
