import { useMatchesForSong, useDiscoverMatchesMutation } from "@/api/matches";
import { useVote } from "@/api/votes";
import { useAuthStore } from "@/stores/auth";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Button,
  ScoreBadge,
  Spinner,
} from "@/components/ui";
import type { Match } from "@/types";

const MATCH_STATUS_STYLES: Record<string, { label: string; className: string }> = {
  verified: { label: "Verified", className: "text-emerald-400 bg-emerald-950/40" },
  rejected: { label: "Rejected", className: "text-red-400 bg-red-950/40" },
  pending:  { label: "Pending",  className: "text-zinc-400 bg-zinc-800/60" },
};

const PLATFORM_LABELS: Record<string, string> = {
  youtube: "YouTube",
  youtube_music: "YT Music",
  soundcloud: "SoundCloud",
  spotify: "Spotify",
  deezer: "Deezer",
  bandcamp: "Bandcamp",
  tidal: "Tidal",
  apple_music: "Apple Music",
};

function formatDurationMatch(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function MatchRow({ match, isAuthenticated }: { match: Match; isAuthenticated: boolean }) {
  const { vote, userVote, isLoading: voteLoading } = useVote(match.id!);
  const status = match.status ?? "pending";
  const statusStyle = MATCH_STATUS_STYLES[status] ?? MATCH_STATUS_STYLES.pending;
  const rawScore = match.score ?? 0;
  const score = rawScore > 1 ? Math.round(rawScore) : Math.round(rawScore * 100);

  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-zinc-800/20 transition-colors">
      {/* Score */}
      <ScoreBadge score={score} className="shrink-0" />

      {/* Track info */}
      <div className="flex-1 min-w-0">
        {match.result.url ? (
          <a
            href={match.result.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-zinc-200 hover:text-accent-needle transition-colors truncate block text-sm"
          >
            {match.result.name}
          </a>
        ) : (
          <p className="font-medium text-zinc-200 truncate text-sm">{match.result.name}</p>
        )}
        <div className="flex items-center gap-2 text-xs text-zinc-500 mt-0.5">
          <span>{PLATFORM_LABELS[match.result.platform] ?? match.result.platform}</span>
          {match.result.duration > 0 && (
            <>
              <span>·</span>
              <span className="font-mono">{formatDurationMatch(match.result.duration)}</span>
            </>
          )}
          {match.submitted_by_username && (
            <>
              <span>·</span>
              <span>by {match.submitted_by_username}</span>
            </>
          )}
        </div>
      </div>

      {/* Status badge */}
      <span className={`shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded ${statusStyle.className}`}>
        {statusStyle.label}
      </span>

      {/* Vote buttons */}
      <div className="shrink-0 flex items-center gap-1">
        <button
          disabled={!isAuthenticated || voteLoading}
          onClick={() => vote("up")}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
            userVote === "up"
              ? "bg-emerald-900/50 text-emerald-400"
              : "text-zinc-500 hover:text-emerald-400 hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed"
          }`}
          title={isAuthenticated ? "Upvote" : "Log in to vote"}
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
          <span>{match.upvotes ?? 0}</span>
        </button>
        <button
          disabled={!isAuthenticated || voteLoading}
          onClick={() => vote("down")}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
            userVote === "down"
              ? "bg-red-900/50 text-red-400"
              : "text-zinc-500 hover:text-red-400 hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed"
          }`}
          title={isAuthenticated ? "Downvote" : "Log in to vote"}
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          <span>{match.downvotes ?? 0}</span>
        </button>
      </div>
    </div>
  );
}

interface SongMatchesSectionProps {
  songId: string;
}

export function SongMatchesSection({ songId }: SongMatchesSectionProps) {
  const { isAuthenticated } = useAuthStore();
  const { data: matchesData, isLoading: matchesLoading } = useMatchesForSong(songId);
  const discoverMatches = useDiscoverMatchesMutation(songId);

  return (
    <Card variant="bordered" className="overflow-hidden">
      <CardHeader className="border-b border-zinc-800/50">
        <CardTitle className="flex items-center gap-2">
          <svg className="w-5 h-5 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          Audio Matches
          {matchesData && matchesData.length > 0 && (
            <Badge variant="muted" size="sm">{matchesData.length}</Badge>
          )}
        </CardTitle>
        <Button
          size="sm"
          variant="outline"
          disabled={discoverMatches.isPending}
          onClick={() => discoverMatches.mutate(undefined)}
        >
          {discoverMatches.isPending ? (
            <Spinner size="sm" />
          ) : (
            <>
              <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Discover
            </>
          )}
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {matchesLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner size="md" />
          </div>
        ) : matchesData && matchesData.length > 0 ? (
          <div className="divide-y divide-zinc-800/50">
            {matchesData.map((match) => (
              <MatchRow key={match.id} match={match} isAuthenticated={isAuthenticated} />
            ))}
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-zinc-500 text-sm">No audio matches found</p>
            <p className="text-xs text-zinc-600 mt-1">Click Discover to search for matches</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
