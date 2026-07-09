import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useResolve, useSearch as useSearchQuery } from "../api/queries";
import { reportError } from "../lib/report-error";
import { DegradedBanner } from "../components/DegradedBanner";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { EntityCard } from "../components/EntityCard";
import { Spinner } from "../components/Spinner";
import { joinArtists } from "../lib/format";

export const Route = createFileRoute("/search")({
  validateSearch: (search: Record<string, unknown>): { q?: string } => {
    const q = search.q;
    return typeof q === "string" && q.length > 0 ? { q } : {};
  },
  component: SearchResults,
});

function SearchResults() {
  const { q } = Route.useSearch();
  const query = q ?? "";
  const { data, isPending, isError, isFetching } = useSearchQuery(query);
  const navigate = useNavigate();
  const resolve = useResolve();

  // A search hit is a provider snapshot preview, not a canonical entity —
  // clicking it resolves the provider ref into the canonical track first
  // (the /tracks/{id} route only serves canonical ids).
  const openHit = (track: { id: string; provider?: string | null; provider_id?: string | null }) => {
    if (!track.provider || !track.provider_id) {
      reportError(null, "That result can't be opened (no source reference).");
      return;
    }
    resolve.mutate(
      { body: { query: `${track.provider}:track:${track.provider_id}` } },
      {
        onSuccess: (res) => {
          const id = res.entity.type === "track" ? res.entity.track?.id : undefined;
          if (id) void navigate({ to: "/tracks/$trackId", params: { trackId: id } });
        },
        onError: (err) => reportError(err, "Couldn't open that result."),
      },
    );
  };

  if (query.trim().length === 0) {
    return (
      <EmptyState
        title="Search spotDL"
        description="Type a track, album, artist, or playlist above to see results."
      />
    );
  }

  // `useSearch` is disabled for an empty query, so a non-empty query that hasn't
  // resolved yet is genuinely loading.
  if (isPending) {
    return (
      <div className="flex justify-center py-16">
        <Spinner label="Searching" className="size-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Search failed"
        description="Something went wrong searching. Try again in a moment."
      />
    );
  }

  const results = data.results;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-xl font-semibold text-fg">
          Results for “{query}”
        </h1>
        {isFetching ? <Spinner label="Refreshing results" /> : null}
      </div>

      <DegradedBanner sources={data.degraded_sources} />

      {results.length === 0 ? (
        <EmptyState
          title="No results"
          description="No tracks matched that search. Try different words, or paste a link on the home page."
        />
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {results.map((track) => (
            <li key={track.id}>
              <EntityCard
                type="track"
                id={track.id}
                name={track.name}
                subtitle={joinArtists(track.artists)}
                imageUrl={track.album?.cover_url}
                onSelect={() => openHit(track)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
