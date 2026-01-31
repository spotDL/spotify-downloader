import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useFindMatchesMutation, useResolveSongMutation } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { useQueueStore } from "@/stores/queue";
import {
  Button,
  Input,
  Card,
  CardContent,
  Badge,
  Spinner,
  PlatformBadge,
} from "@/components/ui";
import { features } from "@/config";
import type { Match, Song } from "@/types";

export const Route = createFileRoute("/matching")({
  component: MatchingPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function MatchingPage() {
  const { isAuthenticated } = useAuthStore();
  const { addItem } = useQueueStore();
  const [searchUrl, setSearchUrl] = useState("");
  const [sourceSong, setSourceSong] = useState<Song | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);

  const findMatchesMutation = useFindMatchesMutation();
  const resolveSongMutation = useResolveSongMutation();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchUrl.trim()) return;

    setSourceSong(null);
    setMatches([]);

    try {
      // First resolve the source song to get full metadata
      const resolveResult = await resolveSongMutation.mutateAsync(searchUrl.trim());
      if (resolveResult.songs && resolveResult.songs.length > 0) {
        setSourceSong(resolveResult.songs[0]);
      }

      // Then find matches
      const result = await findMatchesMutation.mutateAsync({
        sourceUrl: searchUrl.trim(),
        targetPlatforms: TARGET_PLATFORMS,
      });
      setMatches(result.matches);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  const handleDownload = (match: Match) => {
    if (!sourceSong) return;

    addItem(sourceSong, match);
  };

  const isLoading = findMatchesMutation.isPending || resolveSongMutation.isPending;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="relative p-8 bg-gradient-to-br from-purple-900/30 via-zinc-900/80 to-zinc-900/90 rounded-2xl border border-zinc-800/50 shadow-xl overflow-hidden">
        <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full blur-3xl opacity-20 bg-gradient-to-br from-purple-500 to-pink-500" />

        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-white">Cross-Platform Matching</h1>
          </div>
          <p className="text-zinc-400 max-w-2xl">
            Find the same song across different platforms. Enter a Spotify, Deezer, or other music URL
            to discover matching tracks on YouTube, SoundCloud, and more.
          </p>
        </div>
      </div>

      {/* Auth Info */}
      {!isAuthenticated && (
        <Card variant="bordered" className="border-amber-800/50 bg-amber-950/20">
          <CardContent className="flex items-center gap-4">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-amber-200 font-medium">Sign in to contribute</p>
              <p className="text-amber-400/70 text-sm">Vote on matches and help improve results for everyone</p>
            </div>
            <Link to="/auth/login">
              <Button variant="secondary" size="sm">Sign In</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Search Form */}
      <Card variant="bordered" className="bg-zinc-900/50">
        <CardContent className="p-6">
          <form onSubmit={handleSearch}>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Enter a song URL
            </label>
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="w-5 h-5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                </div>
                <Input
                  type="text"
                  value={searchUrl}
                  onChange={(e) => setSearchUrl(e.target.value)}
                  placeholder="https://open.spotify.com/track/..."
                  className="pl-10"
                />
              </div>
              <Button
                type="submit"
                variant="primary"
                isLoading={isLoading}
                disabled={!searchUrl.trim() || isLoading}
              >
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Find Matches
              </Button>
            </div>
            <p className="text-xs text-zinc-500 mt-2">
              Supports Spotify, Deezer, Apple Music, YouTube Music, and more
            </p>
          </form>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <Spinner size="lg" />
          <p className="text-zinc-400">
            {resolveSongMutation.isPending ? "Resolving song..." : "Finding matches..."}
          </p>
        </div>
      )}

      {/* Error State */}
      {(findMatchesMutation.error || resolveSongMutation.error) && (
        <Card variant="bordered" className="border-red-800/50 bg-red-950/20">
          <CardContent className="flex items-center gap-4">
            <div className="p-2 rounded-lg bg-red-500/20">
              <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-red-200 font-medium">Failed to find matches</p>
              <p className="text-red-400/70 text-sm">
                {(findMatchesMutation.error || resolveSongMutation.error) instanceof Error
                  ? (findMatchesMutation.error || resolveSongMutation.error)?.message
                  : "Please check the URL and try again"}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Source Song Card */}
      {sourceSong && !isLoading && (
        <Card variant="bordered" className="overflow-hidden">
          <div className="flex items-stretch">
            {/* Cover Art */}
            <div className="w-32 h-32 shrink-0 bg-zinc-800">
              {sourceSong.cover_url ? (
                <img
                  src={sourceSong.cover_url}
                  alt={sourceSong.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <svg className="w-12 h-12 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>
              )}
            </div>

            {/* Song Info */}
            <CardContent className="flex-1 flex items-center">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="muted" size="sm">Source</Badge>
                  <PlatformBadge platform={sourceSong.platform as any} />
                </div>
                <h3 className="text-xl font-bold text-zinc-100">{sourceSong.name}</h3>
                <p className="text-zinc-400">{sourceSong.artists.join(", ")}</p>
                <div className="flex items-center gap-4 mt-2 text-sm text-zinc-500">
                  {sourceSong.album_name && (
                    <span>{sourceSong.album_name}</span>
                  )}
                  <span>{formatDuration(sourceSong.duration)}</span>
                </div>
              </div>
              <div className="text-right">
                <Badge variant="info" size="md">
                  {matches.length} {matches.length === 1 ? "match" : "matches"}
                </Badge>
              </div>
            </CardContent>
          </div>
        </Card>
      )}

      {/* Matches List */}
      {matches.length > 0 && !isLoading && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-zinc-100">Matches Found</h2>
            <p className="text-sm text-zinc-500">
              Sorted by match score
            </p>
          </div>

          <div className="space-y-3">
            {matches
              .sort((a, b) => b.score - a.score)
              .map((match, index) => (
                <MatchCard
                  key={`${match.target_platform}-${match.target_url}`}
                  match={match}
                  rank={index + 1}
                  onDownload={() => handleDownload(match)}
                  canDownload={features.canDownload && !!sourceSong}
                  isAuthenticated={isAuthenticated}
                />
              ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {sourceSong && matches.length === 0 && !isLoading && (
        <Card variant="bordered" className="bg-zinc-900/50">
          <CardContent className="py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800 flex items-center justify-center">
              <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-zinc-300 mb-2">No matches found</h3>
            <p className="text-zinc-500 max-w-md mx-auto">
              We couldn't find this song on other platforms. This might be a rare track
              or it may not be available elsewhere.
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
  onDownload: () => void;
  canDownload: boolean;
  isAuthenticated: boolean;
}

function MatchCard({ match, rank, onDownload, canDownload, isAuthenticated }: MatchCardProps) {
  const isTop = rank === 1;
  const scoreColor = match.score >= 90
    ? "text-emerald-400"
    : match.score >= 70
    ? "text-yellow-400"
    : "text-zinc-400";

  return (
    <Card
      variant="bordered"
      className={`transition-all ${
        isTop
          ? "border-emerald-700/50 bg-emerald-950/20 ring-1 ring-emerald-500/20"
          : "hover:border-zinc-600 hover:bg-zinc-800/30"
      }`}
    >
      <CardContent>
        <div className="flex items-center gap-4">
          {/* Rank Badge */}
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold shrink-0 ${
              isTop
                ? "bg-gradient-to-br from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-500/20"
                : "bg-zinc-800 text-zinc-400"
            }`}
          >
            #{rank}
          </div>

          {/* Cover Art */}
          <div className="w-14 h-14 rounded-lg bg-zinc-800 shrink-0 overflow-hidden">
            {match.result.cover_url ? (
              <img
                src={match.result.cover_url}
                alt={match.result.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <svg className="w-6 h-6 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>
            )}
          </div>

          {/* Match Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <PlatformBadge platform={match.target_platform as any} />
              {match.match_type === "user" && (
                <Badge variant="premium" size="sm">User Submitted</Badge>
              )}
              {isTop && (
                <Badge variant="success" size="sm">Best Match</Badge>
              )}
              {match.result.verified && (
                <Badge variant="info" size="sm">Verified</Badge>
              )}
            </div>
            <h4 className="font-semibold text-zinc-100 truncate">{match.result.name}</h4>
            <p className="text-sm text-zinc-400 truncate">{match.result.artist}</p>
            {match.result.views !== null && (
              <p className="text-xs text-zinc-500 mt-0.5">
                {match.result.views.toLocaleString()} views
              </p>
            )}
          </div>

          {/* Score */}
          <div className="text-center px-4 border-l border-zinc-800">
            <div className={`text-2xl font-bold ${scoreColor}`}>
              {Math.round(match.score)}%
            </div>
            <div className="text-xs text-zinc-500">match</div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Voting (if authenticated) */}
            {isAuthenticated && (
              <div className="flex items-center gap-1 mr-2">
                <button
                  className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-emerald-400 transition-colors"
                  title="Upvote this match"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
                <button
                  className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-red-400 transition-colors"
                  title="Downvote this match"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
            )}

            {/* External Link */}
            <a
              href={match.target_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Open in new tab"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>

            {/* Download Button */}
            {canDownload && (
              <Button
                variant={isTop ? "primary" : "secondary"}
                size="sm"
                onClick={onDownload}
              >
                <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
