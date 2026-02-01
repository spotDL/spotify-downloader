import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
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
import { CoverArt } from "@/components/ui/cover-art";
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

// ============================================================================
// SCORE INDICATOR - Visual match score display
// ============================================================================

function ScoreIndicator({ score, size = "md" }: { score: number; size?: "sm" | "md" | "lg" }) {
  const getScoreColor = (s: number) => {
    if (s >= 90) return { bg: "from-emerald-500 to-emerald-600", text: "text-emerald-400", glow: "shadow-emerald-500/30" };
    if (s >= 75) return { bg: "from-lime-500 to-lime-600", text: "text-lime-400", glow: "shadow-lime-500/30" };
    if (s >= 60) return { bg: "from-amber-500 to-amber-600", text: "text-amber-400", glow: "shadow-amber-500/30" };
    return { bg: "from-zinc-500 to-zinc-600", text: "text-zinc-400", glow: "shadow-zinc-500/30" };
  };

  const colors = getScoreColor(score);
  const sizeClasses = {
    sm: "w-12 h-12 text-sm",
    md: "w-16 h-16 text-lg",
    lg: "w-20 h-20 text-xl",
  };

  const circumference = 2 * Math.PI * 20;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className={`relative ${sizeClasses[size]} flex items-center justify-center`}>
      {/* Background circle */}
      <svg className="absolute inset-0 w-full h-full -rotate-90">
        <circle
          cx="50%"
          cy="50%"
          r="40%"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          className="text-zinc-800"
        />
        <circle
          cx="50%"
          cy="50%"
          r="40%"
          fill="none"
          stroke="url(#scoreGradient)"
          strokeWidth="3"
          strokeLinecap="round"
          style={{
            strokeDasharray: circumference,
            strokeDashoffset,
            transition: "stroke-dashoffset 1s ease-out",
          }}
        />
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" className={colors.bg.includes("emerald") ? "stop-emerald-400" : colors.bg.includes("lime") ? "stop-lime-400" : colors.bg.includes("amber") ? "stop-amber-400" : "stop-zinc-400"} stopColor="currentColor" />
            <stop offset="100%" className={colors.bg.includes("emerald") ? "stop-emerald-600" : colors.bg.includes("lime") ? "stop-lime-600" : colors.bg.includes("amber") ? "stop-amber-600" : "stop-zinc-600"} stopColor="currentColor" />
          </linearGradient>
        </defs>
      </svg>
      {/* Score text */}
      <span className={`font-bold ${colors.text}`}>{Math.round(score)}%</span>
    </div>
  );
}

// ============================================================================
// WAVEFORM DECORATION - Audio visualization aesthetic element
// ============================================================================

function WaveformDecoration({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-end gap-0.5 h-8 ${className}`}>
      {[3, 5, 8, 6, 9, 4, 7, 5, 8, 6, 4, 7, 5, 3].map((h, i) => (
        <div
          key={i}
          className="w-1 bg-gradient-to-t from-accent-needle/40 to-accent-needle/80 rounded-full"
          style={{
            height: `${h * 10}%`,
            animation: `waveform ${0.8 + i * 0.1}s ease-in-out infinite alternate`,
            animationDelay: `${i * 0.05}s`,
          }}
        />
      ))}
    </div>
  );
}

// ============================================================================
// MATCH CARD - Individual match result with audio equipment aesthetic
// ============================================================================

interface MatchCardProps {
  match: Match;
  rank: number;
  onDownload: () => void;
  canDownload: boolean;
  isAuthenticated: boolean;
}

function MatchCard({ match, rank, onDownload, canDownload, isAuthenticated }: MatchCardProps) {
  const isTop = rank === 1;

  const getScoreLevel = (score: number) => {
    if (score >= 90) return "excellent";
    if (score >= 75) return "good";
    if (score >= 60) return "fair";
    return "low";
  };

  const scoreLevel = getScoreLevel(match.score);

  const cardStyles = {
    excellent: "border-emerald-500/30 bg-gradient-to-r from-emerald-950/30 via-zinc-900/90 to-zinc-900",
    good: "border-lime-500/20 bg-gradient-to-r from-lime-950/20 via-zinc-900/90 to-zinc-900",
    fair: "border-amber-500/20 bg-gradient-to-r from-amber-950/20 via-zinc-900/90 to-zinc-900",
    low: "border-zinc-700/50 bg-zinc-900/90",
  };

  return (
    <div
      className={`relative rounded-2xl border ${cardStyles[scoreLevel]} p-4 transition-all duration-300 hover:scale-[1.01] group overflow-hidden`}
    >
      {/* Top badge for best match */}
      {isTop && (
        <div className="absolute top-0 right-0 px-3 py-1 rounded-bl-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-xs font-bold">
          BEST MATCH
        </div>
      )}

      <div className="flex items-center gap-5">
        {/* Rank indicator */}
        <div className={`flex flex-col items-center justify-center w-14 ${isTop ? "mt-4" : ""}`}>
          <span className={`text-3xl font-black ${isTop ? "text-emerald-400" : "text-zinc-500"}`}>
            {rank}
          </span>
          <span className="text-[10px] text-zinc-600 uppercase tracking-wider">rank</span>
        </div>

        {/* Cover art with platform overlay */}
        <div className="relative group/cover">
          <CoverArt
            src={match.result.cover_url}
            alt={match.result.name}
            size="lg"
            fallbackIcon="track"
            className="ring-2 ring-zinc-800 group-hover/cover:ring-accent-needle/50 transition-all"
          />
          {/* Platform badge overlay */}
          <div className="absolute -bottom-1 -right-1">
            <PlatformBadge platform={match.target_platform as any} />
          </div>
        </div>

        {/* Track info */}
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            {match.match_type === "user" && (
              <Badge variant="premium" size="sm" className="text-[10px]">
                <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Community
              </Badge>
            )}
            {match.result.verified && (
              <Badge variant="info" size="sm" className="text-[10px]">
                <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Verified
              </Badge>
            )}
          </div>

          <h4 className="font-bold text-lg text-zinc-100 truncate group-hover:text-accent-needle transition-colors">
            {match.result.name}
          </h4>

          <p className="text-sm text-zinc-400 truncate">{match.result.artist}</p>

          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span className="font-mono">{formatDuration(match.result.duration)}</span>
            {match.result.views !== null && (
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                {match.result.views.toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {/* Score indicator */}
        <div className="px-4">
          <ScoreIndicator score={match.score} size="md" />
        </div>

        {/* Actions panel */}
        <div className="flex flex-col gap-2 pl-4 border-l border-zinc-800">
          {/* Voting */}
          {isAuthenticated && (
            <div className="flex items-center gap-1">
              <button
                className="p-2 rounded-lg bg-zinc-800/50 hover:bg-emerald-500/20 text-zinc-400 hover:text-emerald-400 transition-all"
                title="Upvote this match"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
              </button>
              <button
                className="p-2 rounded-lg bg-zinc-800/50 hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-all"
                title="Downvote this match"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          )}

          {/* External link */}
          <a
            href={match.target_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-all text-center"
            title="Open in new tab"
          >
            <svg className="w-4 h-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>

          {/* Download */}
          {canDownload && (
            <Button
              variant={isTop ? "primary" : "secondary"}
              size="sm"
              onClick={onDownload}
              className="px-3"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </Button>
          )}
        </div>
      </div>

      {/* Bottom glow effect for top match */}
      {isTop && (
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent" />
      )}
    </div>
  );
}

// ============================================================================
// SOURCE SONG PANEL - Displays the source track being matched
// ============================================================================

function SourceSongPanel({ song, matchCount }: { song: Song; matchCount: number }) {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-zinc-900 via-zinc-900/95 to-zinc-800/90 border border-zinc-800/50">
      {/* Background blur effect */}
      {song.cover_url && (
        <div className="absolute inset-0 overflow-hidden">
          <img
            src={song.cover_url}
            alt=""
            className="w-full h-full object-cover blur-3xl opacity-20 scale-150"
          />
        </div>
      )}

      <div className="relative p-6">
        <div className="flex items-center gap-6">
          {/* Cover Art */}
          <CoverArt
            src={song.cover_url ?? null}
            alt={song.name}
            size="xl"
            fallbackIcon="track"
            className="ring-4 ring-zinc-800 shadow-2xl"
          />

          {/* Song Info */}
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <Badge variant="muted" size="sm" className="bg-zinc-800/80">
                <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
                </svg>
                Source Track
              </Badge>
              <PlatformBadge platform={song.platform as any} />
            </div>

            <h2 className="text-2xl font-black text-zinc-50 tracking-tight">
              {song.name}
            </h2>

            <p className="text-lg text-zinc-400">
              {song.artists.join(", ")}
            </p>

            <div className="flex items-center gap-6 text-sm text-zinc-500">
              {song.album_name && (
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  {song.album_name}
                </span>
              )}
              <span className="font-mono">{formatDuration(song.duration)}</span>
              {song.isrc && (
                <span className="font-mono text-xs bg-zinc-800 px-2 py-0.5 rounded">
                  ISRC: {song.isrc}
                </span>
              )}
            </div>
          </div>

          {/* Match count indicator */}
          <div className="text-center px-6 py-4 bg-zinc-800/50 rounded-xl border border-zinc-700/50">
            <div className="text-4xl font-black text-accent-needle">
              {matchCount}
            </div>
            <div className="text-xs text-zinc-500 uppercase tracking-wider">
              {matchCount === 1 ? "Match" : "Matches"} Found
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN MATCHING PAGE
// ============================================================================

function MatchingPage() {
  const navigate = useNavigate();
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
    navigate({ to: "/queue" });
  };

  const isLoading = findMatchesMutation.isPending || resolveSongMutation.isPending;

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-zinc-900 via-zinc-900/95 to-bg-chassis border border-zinc-800/50">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent-needle/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent-cool/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

        <div className="relative p-8 lg:p-12">
          <div className="flex items-start justify-between">
            <div className="space-y-4 max-w-2xl">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-gradient-to-br from-accent-needle/20 to-accent-needle/5 border border-accent-needle/20">
                  <svg className="w-6 h-6 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <Badge variant="success" size="sm" className="text-xs">
                  Cross-Platform
                </Badge>
              </div>

              <h1 className="text-4xl lg:text-5xl font-black text-zinc-50 tracking-tight">
                Song Matching
              </h1>

              <p className="text-lg text-zinc-400 leading-relaxed">
                Find the same track across YouTube, SoundCloud, and other platforms.
                Paste any music URL to discover matching sources instantly.
              </p>
            </div>

            <WaveformDecoration className="hidden lg:flex opacity-50" />
          </div>
        </div>
      </div>

      {/* Auth Notice */}
      {!isAuthenticated && (
        <div className="flex items-center gap-4 p-4 rounded-xl bg-amber-950/20 border border-amber-800/30">
          <div className="p-2 rounded-lg bg-amber-500/20">
            <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-amber-200 font-medium">Sign in to contribute</p>
            <p className="text-amber-400/70 text-sm">Vote on matches and help improve results for everyone</p>
          </div>
          <Link to="/auth/login">
            <Button variant="secondary" size="sm">Sign In</Button>
          </Link>
        </div>
      )}

      {/* Search Input Panel */}
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-accent-needle/10 via-transparent to-accent-cool/10 rounded-2xl blur-xl" />
        <Card variant="bordered" className="relative bg-zinc-900/80 backdrop-blur-sm border-zinc-800/50">
          <CardContent className="p-6">
            <form onSubmit={handleSearch} className="space-y-4">
              <label className="block text-sm font-semibold text-zinc-300">
                Paste a song URL to find matches
              </label>
              <div className="flex gap-3">
                <div className="flex-1 relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="w-5 h-5 text-zinc-500 group-focus-within:text-accent-needle transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <Input
                    type="text"
                    value={searchUrl}
                    onChange={(e) => setSearchUrl(e.target.value)}
                    placeholder="https://open.spotify.com/track/... or any music URL"
                    className="pl-12 h-12 text-base"
                  />
                </div>
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isLoading={isLoading}
                  disabled={!searchUrl.trim() || isLoading}
                  className="px-8"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Find Matches
                </Button>
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <span>Supported:</span>
                <Badge variant="muted" size="sm" className="text-[10px]">Spotify</Badge>
                <Badge variant="muted" size="sm" className="text-[10px]">Deezer</Badge>
                <Badge variant="muted" size="sm" className="text-[10px]">Apple Music</Badge>
                <Badge variant="muted" size="sm" className="text-[10px]">YouTube Music</Badge>
                <Badge variant="muted" size="sm" className="text-[10px]">SoundCloud</Badge>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-6">
          <div className="relative">
            <Spinner size="lg" />
            <div className="absolute inset-0 animate-ping opacity-20">
              <Spinner size="lg" />
            </div>
          </div>
          <div className="text-center space-y-1">
            <p className="text-zinc-300 font-medium">
              {resolveSongMutation.isPending ? "Resolving song metadata..." : "Searching for matches..."}
            </p>
            <p className="text-sm text-zinc-500">This may take a few seconds</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {(findMatchesMutation.error || resolveSongMutation.error) && (
        <Card variant="bordered" className="border-red-800/50 bg-red-950/20">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 rounded-xl bg-red-500/20">
              <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-red-200 font-semibold">Failed to find matches</p>
              <p className="text-red-400/70 text-sm">
                {(findMatchesMutation.error || resolveSongMutation.error) instanceof Error
                  ? (findMatchesMutation.error || resolveSongMutation.error)?.message
                  : "Please check the URL and try again"}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Source Song Panel */}
      {sourceSong && !isLoading && (
        <SourceSongPanel song={sourceSong} matchCount={matches.length} />
      )}

      {/* Matches List */}
      {matches.length > 0 && !isLoading && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-zinc-100">Matches Found</h2>
              <Badge variant="muted" className="bg-zinc-800">
                {matches.length} {matches.length === 1 ? "result" : "results"}
              </Badge>
            </div>
            <p className="text-sm text-zinc-500 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
              </svg>
              Sorted by match score
            </p>
          </div>

          <div className="space-y-4">
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

      {/* Empty State - No matches found */}
      {sourceSong && matches.length === 0 && !isLoading && (
        <Card variant="bordered" className="bg-zinc-900/50">
          <CardContent className="py-16 text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-zinc-800 flex items-center justify-center">
              <svg className="w-10 h-10 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-zinc-300 mb-2">No matches found</h3>
            <p className="text-zinc-500 max-w-md mx-auto">
              We couldn't find this song on other platforms. This might be a rare track
              or it may not be available elsewhere.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Initial Empty State */}
      {!sourceSong && !isLoading && !findMatchesMutation.error && !resolveSongMutation.error && (
        <Card variant="bordered" className="bg-zinc-900/30 border-dashed">
          <CardContent className="py-16 text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-zinc-800/50 flex items-center justify-center">
              <svg className="w-10 h-10 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-zinc-400 mb-2">Ready to match</h3>
            <p className="text-zinc-500 max-w-md mx-auto">
              Paste a song URL above to find matching tracks across different platforms
            </p>
          </CardContent>
        </Card>
      )}

      {/* CSS for waveform animation */}
      <style>{`
        @keyframes waveform {
          0% { transform: scaleY(0.5); }
          100% { transform: scaleY(1); }
        }
      `}</style>
    </div>
  );
}
