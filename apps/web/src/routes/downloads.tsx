import { createFileRoute } from "@tanstack/react-router";
import { useDownloads } from "../api/downloads";
import { useProgressSocket } from "../api/ws";
import { useFeature } from "../app/config";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { QueueTable } from "../components/QueueTable";
import { Spinner } from "../components/Spinner";

export const Route = createFileRoute("/downloads")({ component: DownloadsPage });

function DownloadsPage() {
  // CONTRACT G — the route exists in every mode, but the queue only renders
  // where downloads are enabled (a direct-URL visit in HOSTED is a dead end).
  if (!useFeature("downloads")) {
    return (
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
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
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight text-fg">Downloads</h1>
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
          description="Enqueue a track, album, or playlist to see it here."
        />
      ) : (
        <QueueTable jobs={query.data.jobs} />
      )}
    </div>
  );
}
