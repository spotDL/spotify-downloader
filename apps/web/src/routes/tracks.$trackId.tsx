import { createFileRoute } from "@tanstack/react-router";
import { useTrack } from "../api/queries";
import { EmptyState } from "../components/EmptyState";
import { EntityCard } from "../components/EntityCard";
import { ErrorState } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { joinMeta } from "../lib/format";

// MERGE: minimal placeholder so the collection pages (Task 8) have a real,
// type-safe `/tracks/$trackId` link target. The full track page — metadata,
// matches + voting + submit-URL, lyrics (incl. synced) + per-track enqueue — is
// Plan 10 Task 7 on a sibling track; keep that richer version on merge.
export const Route = createFileRoute("/tracks/$trackId")({ component: TrackPage });

function TrackPage() {
  const { trackId } = Route.useParams();
  const query = useTrack(trackId);

  if (query.isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Loading" className="size-8" />
      </div>
    );
  }
  if (query.isError) {
    return <ErrorState description="Couldn't load this track." />;
  }

  const track = query.data;
  return (
    <div className="flex flex-col gap-6">
      <EntityCard
        coverUrl={track.album?.cover_url}
        title={track.name}
        subtitle={track.artists.join(", ")}
        meta={joinMeta([track.album?.name, track.year])}
      />
      <EmptyState
        title="Track details"
        description="Matches, voting, and lyrics land in a later task."
      />
    </div>
  );
}
