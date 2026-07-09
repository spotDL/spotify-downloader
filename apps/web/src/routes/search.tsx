import { createFileRoute, Link } from "@tanstack/react-router";
import { useSearch as useSearchQuery } from "../api/queries";
import { DegradedBanner } from "../components/DegradedBanner";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { EntityCard } from "../components/placeholders";
import { Spinner } from "../components/Spinner";
import { formatDuration, joinArtists } from "../lib/format";

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
              <Link
                to="/tracks/$trackId"
                params={{ trackId: track.id }}
                className="block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded-card"
              >
                <EntityCard
                  title={track.name}
                  subtitle={joinArtists(track.artists)}
                  imageUrl={track.album?.cover_url}
                  badge={
                    <span className="text-xs text-muted tabular-nums">
                      {formatDuration(track.duration_ms)}
                    </span>
                  }
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
