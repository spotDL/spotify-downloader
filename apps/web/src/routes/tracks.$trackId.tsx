import { createFileRoute } from "@tanstack/react-router";
import { useTrack } from "../api/queries";
import { ErrorState } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { formatDuration, joinArtists } from "../lib/format";

// Minimal metadata header (Task 6) — the match list, voting, submit-URL form,
// and synced-lyrics viewer are added in Task 7.
export const Route = createFileRoute("/tracks/$trackId")({
  component: TrackPage,
});

function TrackPage() {
  const { trackId } = Route.useParams();
  const track = useTrack(trackId);

  if (track.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading track" className="size-8" />
      </div>
    );
  }

  if (track.isError) {
    return (
      <ErrorState
        title="Couldn't load this track"
        description="The track may not exist, or the server is unreachable."
      />
    );
  }

  const t = track.data;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="size-40 shrink-0 overflow-hidden rounded-card bg-black/5 dark:bg-white/10">
          {t.album?.cover_url ? (
            <img
              src={t.album.cover_url}
              alt=""
              className="size-full object-cover"
            />
          ) : null}
        </div>
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold text-fg">{t.name}</h1>
          <p className="text-muted">{joinArtists(t.artists)}</p>
          <p className="text-sm text-muted">
            {t.album?.name ? <span>{t.album.name}</span> : null}
            {t.year ? <span> · {t.year}</span> : null}
            <span> · {formatDuration(t.duration_ms)}</span>
          </p>
        </div>
      </header>
    </div>
  );
}
