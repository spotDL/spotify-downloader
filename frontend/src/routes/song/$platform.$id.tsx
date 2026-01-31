import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useTrack, useFindMatchesMutation } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { EntityHeader } from "@/components/entity";
import { Card, CardContent, Button, Badge, Spinner, PlatformBadge } from "@/components/ui";
import { features } from "@/config";
import type { Match } from "@/types";

export const Route = createFileRoute("/song/$platform/$id" as const)({
  component: SongPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function SongPage() {
  const navigate = useNavigate();
  const { platform, id } = Route.useParams();
  const { data: track, isLoading, error } = useTrack(platform, id);
  const findMatchesMutation = useFindMatchesMutation();
  const addToQueue = useQueueStore((state) => state.addItem);

  const handleFindMatches = async () => {
    if (!track) return;

    try {
      await findMatchesMutation.mutateAsync({
        sourceUrl: track.url,
        targetPlatforms: TARGET_PLATFORMS,
      });
    } catch (err) {
      console.error("Failed to find matches:", err);
    }
  };

  const handleDownload = (match: Match) => {
    if (!track || !features.canDownload) return;
    addToQueue(track, match);
    navigate({ to: "/queue" });
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading track...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-red-400">Failed to load track</p>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
          <Link to="/" className="text-emerald-400 hover:underline mt-4 inline-block">
            Back to search
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (!track) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Track not found</p>
          <Link to="/" className="text-emerald-400 hover:underline mt-4 inline-block">
            Back to search
          </Link>
        </CardContent>
      </Card>
    );
  }

  const matches = findMatchesMutation.data?.matches || [];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <nav className="text-sm text-zinc-500">
        <Link to="/" className="hover:text-zinc-300">
          Home
        </Link>
        <span className="mx-2">/</span>
        <span className="text-zinc-300">{track.name}</span>
      </nav>

      {/* Header */}
      <EntityHeader
        type="track"
        name={track.name}
        platform={track.platform}
        imageUrl={track.cover_url}
        subtitle={track.artists.join(", ")}
        metadata={{
          year: track.year,
          genres: track.genres,
        }}
      />

      {/* Track Details */}
      <Card variant="bordered">
        <CardContent className="space-y-4">
          <h3 className="text-lg font-semibold text-zinc-100">Track Details</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-zinc-500 block">Duration</span>
              <span className="text-zinc-200">{formatDuration(track.duration)}</span>
            </div>
            {track.album_name && (
              <div>
                <span className="text-zinc-500 block">Album</span>
                <span className="text-zinc-200">{track.album_name}</span>
              </div>
            )}
            {track.year && (
              <div>
                <span className="text-zinc-500 block">Year</span>
                <span className="text-zinc-200">{track.year}</span>
              </div>
            )}
            {track.isrc && (
              <div>
                <span className="text-zinc-500 block">ISRC</span>
                <span className="text-zinc-200 font-mono text-xs">{track.isrc}</span>
              </div>
            )}
            {track.track_number && (
              <div>
                <span className="text-zinc-500 block">Track #</span>
                <span className="text-zinc-200">
                  {track.track_number}
                  {track.disc_number && track.disc_number > 1 && ` (Disc ${track.disc_number})`}
                </span>
              </div>
            )}
            {track.explicit && (
              <div>
                <span className="text-zinc-500 block">Rating</span>
                <Badge variant="warning" size="sm">Explicit</Badge>
              </div>
            )}
          </div>
          <div className="pt-2">
            <a
              href={track.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors inline-flex items-center gap-1"
            >
              Open on {track.platform.replace("_", " ")}
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Find Matches */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-zinc-100">Download Sources</h2>
          {!findMatchesMutation.data && (
            <Button
              variant="primary"
              onClick={handleFindMatches}
              isLoading={findMatchesMutation.isPending}
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Find Matches
            </Button>
          )}
        </div>

        {findMatchesMutation.isPending && (
          <div className="flex items-center justify-center py-12 gap-4">
            <Spinner />
            <span className="text-zinc-400">Searching for matches...</span>
          </div>
        )}

        {findMatchesMutation.error && (
          <Card variant="bordered" className="border-red-900/50">
            <CardContent className="py-4">
              <p className="text-red-400">Failed to find matches</p>
              <p className="text-sm text-zinc-500 mt-1">
                {findMatchesMutation.error instanceof Error
                  ? findMatchesMutation.error.message
                  : "An error occurred"}
              </p>
            </CardContent>
          </Card>
        )}

        {matches.length > 0 && (
          <div className="space-y-3">
            {matches.map((match, index) => {
              const isTop = index === 0;

              return (
                <Card
                  key={match.id}
                  variant="bordered"
                  className={
                    isTop
                      ? "border-emerald-800/50 shadow-lg shadow-emerald-900/20"
                      : ""
                  }
                >
                  <CardContent>
                    {isTop && (
                      <div className="absolute -top-2 right-4 px-2 py-0.5 bg-emerald-500 text-white text-xs font-semibold rounded-full shadow-lg">
                        Top Pick
                      </div>
                    )}

                    <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <PlatformBadge platform={match.target_platform as any} />
                          {match.match_type === "user" && (
                            <Badge variant="premium" size="sm">
                              User Verified
                            </Badge>
                          )}
                          {match.match_score !== null && (
                            <span
                              className={`text-sm font-semibold ${
                                match.match_score >= 90
                                  ? "text-emerald-400"
                                  : match.match_score >= 70
                                  ? "text-yellow-400"
                                  : "text-zinc-400"
                              }`}
                            >
                              {Math.round(match.match_score)}% match
                            </span>
                          )}
                        </div>
                        <a
                          href={match.target_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-zinc-400 hover:text-zinc-200 truncate block transition-colors"
                        >
                          {match.target_url}
                        </a>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1 text-sm bg-zinc-800/50 rounded-lg px-2 py-1">
                          <span className="font-medium text-zinc-300 min-w-[2ch] text-center">
                            {match.upvotes - match.downvotes}
                          </span>
                        </div>
                        {features.canDownload ? (
                          <Button
                            size="sm"
                            variant={isTop ? "primary" : "outline"}
                            onClick={() => handleDownload(match)}
                          >
                            <svg
                              className="w-4 h-4 mr-1.5"
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
                            Download
                          </Button>
                        ) : (
                          <a
                            href={match.target_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button size="sm" variant={isTop ? "primary" : "outline"}>
                              <svg
                                className="w-4 h-4 mr-1.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                />
                              </svg>
                              Open
                            </Button>
                          </a>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {findMatchesMutation.data && matches.length === 0 && (
          <Card variant="bordered">
            <CardContent className="py-8 text-center">
              <p className="text-zinc-400">No matches found for this track</p>
              <p className="text-sm text-zinc-500 mt-2">
                Try searching on a different platform or submit a match yourself.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
