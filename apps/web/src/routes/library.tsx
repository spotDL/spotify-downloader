import { createFileRoute } from "@tanstack/react-router";
import { useDownloads } from "../api/downloads";
import { useFeature } from "../app/config";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { QueueTable } from "../components/QueueTable";
import { Spinner } from "../components/Spinner";

export const Route = createFileRoute("/library")({ component: LibraryPage });

function LibraryPage() {
  if (!useFeature("library")) {
    return (
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        <EmptyState
          title="Library"
          description="The library is not available on this server."
        />
      </div>
    );
  }
  return <LibraryList />;
}

function LibraryList() {
  // The library is the completed-jobs view (`status=completed`), grouped by
  // batch with per-file download links and a per-batch `.spotdl` save file.
  // (m3u playlists have no HTTP endpoint — their paths are server-local, emitted
  // only on the WS `batch_finished` frame — so they are not linkable here.)
  const query = useDownloads({ status: "completed", limit: 100 });

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight text-fg">Library</h1>
      {query.isPending ? (
        <div className="flex justify-center py-16">
          <Spinner label="Loading your library" className="size-8" />
        </div>
      ) : query.isError ? (
        <ErrorState
          description="Couldn't load your library."
          action={
            <Button variant="secondary" onClick={() => void query.refetch()}>
              Retry
            </Button>
          }
        />
      ) : query.data.jobs.length === 0 ? (
        <EmptyState
          title="Nothing downloaded yet"
          description="Completed downloads show up here with file links."
        />
      ) : (
        <QueueTable jobs={query.data.jobs} showBatchSaveFile />
      )}
    </div>
  );
}
