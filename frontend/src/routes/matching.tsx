import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useFindMatchesMutation } from "@/api";
import { useAuthStore } from "@/stores/auth";
import {
  Button,
  Input,
  Card,
  CardContent,
  Badge,
  Loading,
  PlatformBadge,
} from "@/components/ui";
import type { Match } from "@/types";

export const Route = createFileRoute("/matching")({
  component: MatchingPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function MatchingPage() {
  const { isAuthenticated } = useAuthStore();
  const [searchUrl, setSearchUrl] = useState("");
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);

  const findMatchesMutation = useFindMatchesMutation();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchUrl.trim()) return;

    setSourceUrl(null);
    setMatches([]);

    try {
      const result = await findMatchesMutation.mutateAsync({
        sourceUrl: searchUrl.trim(),
        targetPlatforms: TARGET_PLATFORMS,
      });
      setSourceUrl(result.source_url);
      setMatches(result.matches);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Match Voting</h1>
        <p className="text-gray-400 mt-1">
          Help improve match quality by voting on song matches. Your votes help
          others find the best downloads.
        </p>
      </div>

      {/* Auth Warning */}
      {!isAuthenticated && (
        <Card variant="bordered" className="border-yellow-700 bg-yellow-900/20">
          <CardContent className="flex items-center gap-3">
            <svg
              className="w-5 h-5 text-yellow-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-yellow-400">
              Sign in to vote on matches and contribute to the community
            </p>
          </CardContent>
        </Card>
      )}

      {/* Search Form */}
      <form onSubmit={handleSearch} className="max-w-2xl">
        <div className="flex gap-2">
          <Input
            type="text"
            value={searchUrl}
            onChange={(e) => setSearchUrl(e.target.value)}
            placeholder="Enter a song URL to see matches..."
            className="flex-1"
          />
          <Button
            type="submit"
            isLoading={findMatchesMutation.isPending}
            disabled={!searchUrl.trim()}
          >
            Find Matches
          </Button>
        </div>
      </form>

      {/* Loading */}
      {findMatchesMutation.isPending && (
        <div className="flex justify-center py-8">
          <Loading text="Finding matches..." />
        </div>
      )}

      {/* Error */}
      {findMatchesMutation.error && (
        <Card variant="bordered" className="border-red-700">
          <CardContent>
            <p className="text-red-400">
              {findMatchesMutation.error instanceof Error
                ? findMatchesMutation.error.message
                : "Failed to find matches"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Source URL Info */}
      {sourceUrl && !findMatchesMutation.isPending && (
        <Card variant="bordered">
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-zinc-700 rounded flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-zinc-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                  />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-zinc-100">Source Track</h3>
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-emerald-400 hover:text-emerald-300 truncate block"
                >
                  {sourceUrl}
                </a>
              </div>
              <Badge variant="info">{matches.length} matches</Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Matches */}
      {matches.length > 0 && !findMatchesMutation.isPending && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-zinc-100">
            {matches.length} Match{matches.length !== 1 ? "es" : ""} Found
          </h2>

          <div className="space-y-3">
            {matches
              .sort((a, b) => b.score - a.score)
              .map((match, index) => (
                <MatchCard
                  key={`${match.target_platform}-${match.target_url}`}
                  match={match}
                  rank={index + 1}
                />
              ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {sourceUrl && matches.length === 0 && !findMatchesMutation.isPending && (
        <Card variant="bordered">
          <CardContent className="text-center py-8">
            <p className="text-zinc-400">No matches found for this song</p>
            <p className="text-sm text-zinc-500 mt-2">
              Try a different song or submit a match yourself
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface MatchCardProps {
  match: Match;
  rank: number;
}

function MatchCard({ match, rank }: MatchCardProps) {
  const isTop = rank === 1;

  return (
    <Card
      variant="bordered"
      className={`transition-colors ${
        isTop
          ? "border-emerald-800/50 bg-emerald-950/20"
          : "hover:border-zinc-600"
      }`}
    >
      <CardContent>
        <div className="flex items-center gap-4">
          {/* Rank */}
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
              isTop
                ? "bg-emerald-600 text-white"
                : "bg-zinc-700 text-zinc-300"
            }`}
          >
            #{rank}
          </div>

          {/* Match Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <PlatformBadge platform={match.target_platform as any} />
              {match.match_type === "user" && (
                <Badge variant="premium" size="sm">User Submitted</Badge>
              )}
              {isTop && (
                <Badge variant="success" size="sm">Top Pick</Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-sm text-zinc-300 font-medium">
                {match.result.name}
              </span>
              <span className="text-sm text-zinc-500">
                {match.result.artist}
              </span>
            </div>
            <a
              href={match.target_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-emerald-400 hover:text-emerald-300 truncate block mt-1"
            >
              {match.target_url}
            </a>
          </div>

          {/* Score and Confidence */}
          <div className="text-right space-y-1">
            <div
              className={`text-lg font-bold ${
                match.score >= 90
                  ? "text-emerald-400"
                  : match.score >= 70
                  ? "text-yellow-400"
                  : "text-zinc-400"
              }`}
            >
              {Math.round(match.score)}%
            </div>
            <div className="text-xs text-zinc-500">
              {Math.round(match.confidence * 100)}% confidence
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
