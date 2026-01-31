import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useFindMatchesMutation, useCreateVote } from "@/api";
import { useAuthStore } from "@/stores/auth";
import {
  Button,
  Input,
  Card,
  CardContent,
  Badge,
  Loading,
} from "@/components/ui";
import type { Song, Match } from "@/types";

export const Route = createFileRoute("/matching")({
  component: MatchingPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function MatchingPage() {
  const { isAuthenticated } = useAuthStore();
  const [searchUrl, setSearchUrl] = useState("");
  const [song, setSong] = useState<Song | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);

  const findMatchesMutation = useFindMatchesMutation();
  const createVoteMutation = useCreateVote();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchUrl.trim()) return;

    setSong(null);
    setMatches([]);

    try {
      const result = await findMatchesMutation.mutateAsync({
        sourceUrl: searchUrl.trim(),
        targetPlatforms: TARGET_PLATFORMS,
      });
      setSong(result.song);
      setMatches(result.matches);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  const handleVote = async (matchId: string, voteType: "up" | "down") => {
    if (!isAuthenticated) {
      alert("Please log in to vote");
      return;
    }

    try {
      await createVoteMutation.mutateAsync({
        match_id: matchId,
        vote_type: voteType,
      });
      // Update local state optimistically
      setMatches((prev) =>
        prev.map((m) =>
          m.id === matchId
            ? {
                ...m,
                upvotes: voteType === "up" ? m.upvotes + 1 : m.upvotes,
                downvotes: voteType === "down" ? m.downvotes + 1 : m.downvotes,
              }
            : m
        )
      );
    } catch (error) {
      console.error("Vote failed:", error);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
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

      {/* Song Info */}
      {song && !findMatchesMutation.isPending && (
        <Card variant="bordered">
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gray-700 rounded flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-gray-500"
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
              <div>
                <h3 className="font-semibold text-gray-100">{song.name}</h3>
                <p className="text-sm text-gray-400">
                  {song.artists.join(", ")} •{" "}
                  {formatDuration(song.duration_seconds)}
                </p>
              </div>
              <Badge variant="info" className="ml-auto">
                {song.platform}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Matches */}
      {matches.length > 0 && !findMatchesMutation.isPending && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-100">
            {matches.length} Match{matches.length !== 1 ? "es" : ""} Found
          </h2>

          <div className="space-y-3">
            {matches
              .sort((a, b) => b.upvotes - b.downvotes - (a.upvotes - a.downvotes))
              .map((match, index) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  rank={index + 1}
                  onVote={handleVote}
                  isVoting={createVoteMutation.isPending}
                  canVote={isAuthenticated}
                />
              ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {song && matches.length === 0 && !findMatchesMutation.isPending && (
        <Card variant="bordered">
          <CardContent className="text-center py-8">
            <p className="text-gray-400">No matches found for this song</p>
            <p className="text-sm text-gray-500 mt-2">
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
  onVote: (matchId: string, type: "up" | "down") => void;
  isVoting: boolean;
  canVote: boolean;
}

function MatchCard({ match, rank, onVote, isVoting, canVote }: MatchCardProps) {
  const netVotes = match.upvotes - match.downvotes;

  return (
    <Card
      variant="bordered"
      className="hover:border-gray-600 transition-colors"
    >
      <CardContent>
        <div className="flex items-center gap-4">
          {/* Rank */}
          <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm font-bold">
            #{rank}
          </div>

          {/* Vote Buttons */}
          <div className="flex flex-col items-center gap-1">
            <button
              onClick={() => onVote(match.id, "up")}
              disabled={isVoting || !canVote}
              className="p-1 hover:bg-green-900/50 rounded transition-colors disabled:opacity-50"
              title={canVote ? "Upvote" : "Sign in to vote"}
            >
              <svg
                className="w-5 h-5 text-green-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 15l7-7 7 7"
                />
              </svg>
            </button>
            <span
              className={`text-sm font-medium ${
                netVotes > 0
                  ? "text-green-400"
                  : netVotes < 0
                  ? "text-red-400"
                  : "text-gray-400"
              }`}
            >
              {netVotes}
            </span>
            <button
              onClick={() => onVote(match.id, "down")}
              disabled={isVoting || !canVote}
              className="p-1 hover:bg-red-900/50 rounded transition-colors disabled:opacity-50"
              title={canVote ? "Downvote" : "Sign in to vote"}
            >
              <svg
                className="w-5 h-5 text-red-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
          </div>

          {/* Match Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Badge
                variant={match.match_type === "user" ? "success" : "default"}
              >
                {match.target_platform}
              </Badge>
              {match.match_type === "user" && (
                <Badge variant="info">User Submitted</Badge>
              )}
              {match.match_score !== null && (
                <span className="text-sm text-gray-400">
                  {Math.round(match.match_score)}% confidence
                </span>
              )}
            </div>
            <a
              href={match.target_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-400 hover:text-blue-300 truncate block mt-1"
            >
              {match.target_url}
            </a>
          </div>

          {/* Stats */}
          <div className="text-right text-sm">
            <p className="text-green-400">▲ {match.upvotes}</p>
            <p className="text-red-400">▼ {match.downvotes}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
