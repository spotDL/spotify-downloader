import { useState } from "react";
import { Link } from "@tanstack/react-router";
import type { UseQueryResult } from "@tanstack/react-query";
import type { TrackOut } from "../api/generated/types.gen";
import { isApiError } from "../api/errors";
import { useSubmitDownload } from "../api/downloads";
import { formatDuration } from "../lib/format";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { Feature } from "./Feature";
import { Spinner } from "./Spinner";
import { toast } from "./Toasts";

export type CollectionHeader = {
  title: string;
  subtitle?: string | null;
  meta?: string | null;
  coverUrl?: string | null;
};

// The album/artist/playlist pages share one shape: a metadata header + a track
// list linking to each track page (CONTRACT G/H). Albums & playlists also get an
// "Enqueue all" button (a downloadable batch); an artist does NOT — per Plan 8's
// `unsupported_entity` rule an artist isn't a batch, so enqueue is per-track via
// the track pages. A route opts in by passing `enqueueQueryOf`.
export function CollectionView<T, E = unknown>({
  query,
  toHeader,
  toTracks,
  enqueueQueryOf,
}: {
  query: UseQueryResult<T, E>;
  toHeader: (data: T) => CollectionHeader;
  toTracks: (data: T) => TrackOut[];
  enqueueQueryOf?: (data: T) => string;
}) {
  if (query.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading" className="size-8" />
      </div>
    );
  }
  if (query.isError) {
    return (
      <ErrorState
        description={
          isApiError(query.error)
            ? query.error.message
            : "Couldn't load this page."
        }
        action={
          <Button variant="secondary" onClick={() => void query.refetch()}>
            Retry
          </Button>
        }
      />
    );
  }

  const data = query.data;
  const header = toHeader(data);
  const tracks = toTracks(data);
  const enqueueQuery = enqueueQueryOf?.(data);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {header.coverUrl ? (
          <img
            src={header.coverUrl}
            alt=""
            className="size-32 shrink-0 rounded-card object-cover shadow-card"
          />
        ) : null}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-2xl font-semibold tracking-tight text-fg">
            {header.title}
          </h1>
          {header.subtitle ? (
            <p className="truncate text-muted">{header.subtitle}</p>
          ) : null}
          {header.meta ? (
            <p className="mt-1 text-sm text-muted">{header.meta}</p>
          ) : null}
        </div>
        {enqueueQuery ? (
          <Feature flag="downloads">
            <EnqueueAllButton query={enqueueQuery} />
          </Feature>
        ) : null}
      </header>

      {tracks.length === 0 ? (
        <EmptyState
          title="No tracks"
          description="This collection has no listed tracks."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {tracks.map((track) => (
            <li key={track.id}>
              <Link
                to="/tracks/$trackId"
                params={{ trackId: track.id }}
                className="flex items-center gap-3 rounded-card border border-black/10 bg-surface px-3 py-2 transition-colors hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-white/10 dark:hover:bg-white/5"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-fg">{track.name}</p>
                  {track.artists.length > 0 ? (
                    <p className="truncate text-sm text-muted">
                      {track.artists.join(", ")}
                    </p>
                  ) : null}
                </div>
                <span className="shrink-0 text-sm tabular-nums text-muted">
                  {formatDuration(track.duration_ms)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// The "Enqueue all" action: POST /downloads with the entity query (the server
// expands it into N jobs). On success a toast fires and a persistent link to the
// queue appears; useSubmitDownload already invalidates the downloads cache.
function EnqueueAllButton({ query }: { query: string }) {
  const submit = useSubmitDownload();
  const [enqueued, setEnqueued] = useState(false);

  return (
    <div className="flex shrink-0 flex-col items-start gap-1 sm:items-end">
      <Button
        disabled={submit.isPending}
        onClick={() =>
          submit.mutate(
            { body: { query } },
            {
              onSuccess: () => {
                setEnqueued(true);
                toast.info("Added to the download queue.");
              },
              onError: (error) => {
                if (isApiError(error)) toast.fromApiError(error);
                else toast.error("Couldn't start the download.");
              },
            },
          )
        }
      >
        {submit.isPending ? "Enqueuing…" : "Enqueue all"}
      </Button>
      {enqueued ? (
        <Link
          to="/downloads"
          className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-100"
        >
          View downloads →
        </Link>
      ) : null}
    </div>
  );
}
