import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useMemo, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useInternalSong,
  useRefreshSongMetadata,
  useMetadataSnapshots,
  useFullEnrichment,
  useAllLyrics,
  fetchAllLyrics,
  useSubmitLyrics,
  entityKeys,
} from "@/api/entities";
import {
  matchKeys,
  useFindMatchesMutation,
  useMatchesForSong,
  useLyrics,
  hasLyrics,
  toLyrics,
  useCreateReport,
  useMatchPreview,
  useSubmitMatch,
  useCreateVote,
  useDeleteVote,
  useMatchVotes,
} from "@/api";
import { useUpdateMatchStatus } from "@/api/admin";
import { useQueueStore } from "@/stores/queue";
import { useAuthStore } from "@/stores/auth";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Button,
  RefreshMetadataButton,
  useToast,
  EntityErrorCard,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { Spinner } from "@/components/ui";
import { MatchScoreGauge } from "@/components/ui/match-gauge";
import { LyricsDisplay, MultiSourceLyricsDisplay } from "@/components/ui/lyrics-display";
import { MetadataPanel, MetadataField } from "@/components/ui/metadata-source-badge";
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import { ReportModal } from "@/components/ui/report-modal";
import { MetadataSourceSelector } from "@/components/ui/metadata-source-selector";
import { MetadataComparisonTable } from "@/components/ui/metadata-comparison";
import { SubmitLyricsModal } from "@/components/ui/submit-lyrics-modal";
import { useDevConfig } from "@/contexts/DevConfigContext";
import type { Match, AudioFeatures, CreateMetadataReportRequest } from "@/types";

// Reputation threshold for verification privileges
const VERIFICATION_REP_THRESHOLD = 100;

export const Route = createFileRoute("/song/$id")({
  component: SongPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp", "piped"];

/** Platforms that are metadata sources, not audio targets — we surface them as tied cross-platform matches */
const METADATA_SOURCE_PLATFORMS = new Set(["spotify", "deezer", "apple_music", "tidal", "musicbrainz", "discogs"]);

/** Platforms that support downloading (via yt-dlp or provider hooks) — shown only in self-hosted mode */
const DOWNLOADABLE_PLATFORMS = new Set(["youtube", "youtube_music", "soundcloud", "bandcamp", "piped"]);

function mergeMatches(existing: Match[], incoming: Match[]): Match[] {
  const merged = new Map<string, Match>();

  const mergeIn = (match: Match) => {
    const key = `${match.target_platform}:${match.target_url}`;
    const current = merged.get(key);
    if (!current) {
      merged.set(key, match);
      return;
    }

    merged.set(key, {
      ...current,
      ...match,
      id: match.id ?? current.id,
      source_song_id: match.source_song_id ?? current.source_song_id,
      target_song_id: match.target_song_id ?? current.target_song_id,
      status: match.status ?? current.status,
      upvotes: match.upvotes ?? current.upvotes,
      downvotes: match.downvotes ?? current.downvotes,
      net_votes: match.net_votes ?? current.net_votes,
      submitted_by_username: match.submitted_by_username ?? current.submitted_by_username,
      verified_by_username: match.verified_by_username ?? current.verified_by_username,
      result: {
        ...current.result,
        ...match.result,
      },
    });
  };

  existing.forEach(mergeIn);
  incoming.forEach(mergeIn);

  return Array.from(merged.values()).sort((a, b) => b.score - a.score);
}

/**
 * Build synthetic Match objects from metadata source snapshots.
 * When deezer/spotify/etc. are present as metadata sources, they represent
 * verified cross-platform links to the same song.
 */
function buildMetadataSourceMatches(
  snapshots: Array<{
    id: string;
    source: string;
    confidence: number;
    data: Record<string, unknown> | { [key: string]: unknown };
  }>,
  songId: string
): Match[] {
  return snapshots
    .filter((s) => {
      // Only include metadata platforms that have a URL
      if (!METADATA_SOURCE_PLATFORMS.has(s.source)) return false;
      const url = s.data?.url;
      return typeof url === "string" && url.startsWith("http");
    })
    .map((s): Match => {
      const d = s.data as Record<string, unknown>;
      const url = String(d.url || "");
      const artists = Array.isArray(d.artists)
        ? (d.artists as string[])
        : [];
      const artist = typeof d.artist === "string" ? d.artist : artists[0] || "Unknown";
      return {
        id: `metadata-${s.source}-${s.id}`,
        source_url: "",
        source_song_id: songId,
        source_platform: "spotify",
        target_url: url,
        target_song_id: "",
        target_platform: s.source,
        score: Math.round(s.confidence * 100),
        confidence: s.confidence,
        match_type: "metadata" as const,
        status: "verified" as const,
        upvotes: 0,
        downvotes: 0,
        net_votes: 0,
        result: {
          name: typeof s.data.name === "string" ? s.data.name : "Unknown",
          artists: artists.length > 0 ? artists : [artist],
          artist,
          duration: typeof s.data.duration === "number" ? s.data.duration : 0,
          platform: s.source,
          platform_id: typeof s.data.platform_id === "string" ? s.data.platform_id : "",
          url,
          album_name: typeof s.data.album_name === "string" ? s.data.album_name : null,
          cover_url: typeof s.data.cover_url === "string" ? s.data.cover_url : null,
          views: null,
          explicit: Boolean(s.data.explicit),
          verified: true,
        },
      } satisfies Match;
    });
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);
    return () => clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debouncedValue;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

// Key names for music notation
const KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Key family colors for visual distinction
const KEY_FAMILY_COLORS: Record<string, string> = {
  "C": "bg-red-900/30 text-red-400 border-red-800/50",
  "C#": "bg-rose-900/30 text-rose-400 border-rose-800/50",
  "D": "bg-orange-900/30 text-orange-400 border-orange-800/50",
  "D#": "bg-amber-900/30 text-amber-400 border-amber-800/50",
  "E": "bg-yellow-900/30 text-yellow-400 border-yellow-800/50",
  "F": "bg-lime-900/30 text-lime-400 border-lime-800/50",
  "F#": "bg-green-900/30 text-green-400 border-green-800/50",
  "G": "bg-emerald-900/30 text-emerald-400 border-emerald-800/50",
  "G#": "bg-teal-900/30 text-teal-400 border-teal-800/50",
  "A": "bg-cyan-900/30 text-cyan-400 border-cyan-800/50",
  "A#": "bg-sky-900/30 text-sky-400 border-sky-800/50",
  "B": "bg-blue-900/30 text-blue-400 border-blue-800/50",
};

// Audio feature descriptions for tooltips
const FEATURE_DESCRIPTIONS: Record<string, string> = {
  bpm: "Beats per minute - the tempo of the track",
  energy: "Intensity and activity level of the track (0-100%)",
  danceability: "How suitable the track is for dancing (0-100%)",
  valence: "Musical positiveness - happy/cheerful vs sad/angry (0-100%)",
  speechiness: "Presence of spoken words in the track (0-100%)",
  acousticness: "Confidence the track is acoustic (0-100%)",
  instrumentalness: "Likelihood the track has no vocals (0-100%)",
  liveness: "Presence of a live audience (0-100%)",
  loudness: "Overall loudness in decibels (dB)",
  time_signature: "Beats per measure (e.g., 4/4, 3/4)",
};

// Color coding by intensity level
function getIntensityColor(value: number): string {
  if (value >= 80) return "bg-accent-peak";
  if (value >= 60) return "bg-accent-needle";
  if (value >= 40) return "bg-accent-warm";
  if (value >= 20) return "bg-accent-safe";
  return "bg-accent-cool";
}

function SongPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = Route.useParams();
  const { data: song, isLoading, error } = useInternalSong(id);
  const { data: lyricsData, isLoading: lyricsLoading } = useLyrics(id, { enabled: !!song });
  const { data: allLyricsData, isLoading: allLyricsLoading } = useAllLyrics(id, { enabled: !!song });
  const { data: existingMatches, isLoading: existingMatchesLoading } = useMatchesForSong(id);
  const findMatchesMutation = useFindMatchesMutation();
  const createReportMutation = useCreateReport();
  const refreshMetadata = useRefreshSongMetadata();
  const addItem = useQueueStore((state) => state.addItem);
  const { isAuthenticated } = useAuthStore();
  const { success: showSuccess, error: showError } = useToast();
  const { features } = useDevConfig();

  const [showReportModal, setShowReportModal] = useState(false);
  const [matches, setMatches] = useState<Match[]>([]);
  const [matchesLoaded, setMatchesLoaded] = useState(false);
  const [autoSearchTriggered, setAutoSearchTriggered] = useState(false);
  const [showTechnicalMetadata, setShowTechnicalMetadata] = useState(false);
  const [showAllFeatures, setShowAllFeatures] = useState(false);

  // Multi-source metadata state
  const [activeMetadataSource, setActiveMetadataSource] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  // Multi-source lyrics state
  const [activeLyricsSource, setActiveLyricsSource] = useState<string | null>(null);
  const [fetchingAllLyrics, setFetchingAllLyrics] = useState(false);
  const [showSubmitLyrics, setShowSubmitLyrics] = useState(false);

  // Match submission state
  const [showSubmitMatch, setShowSubmitMatch] = useState(false);
  const [submitMatchUrl, setSubmitMatchUrl] = useState("");
  const [submitMatchPlatform, setSubmitMatchPlatform] = useState("youtube");
  const debouncedSubmitMatchUrl = useDebouncedValue(submitMatchUrl.trim(), 450);
  const submitMatchMutation = useSubmitMatch();
  const updateMatchStatus = useUpdateMatchStatus();
  const submitLyricsMutation = useSubmitLyrics();
  const {
    data: previewData,
    isLoading: previewLoading,
    error: previewError,
  } = useMatchPreview(
    debouncedSubmitMatchUrl,
    showSubmitMatch && debouncedSubmitMatchUrl.length > 0
  );

  // Check if user can verify matches (admin or high reputation)
  const { user } = useAuthStore();
  const canVerifyMatches = user && (user.is_admin || user.reputation_score >= VERIFICATION_REP_THRESHOLD);

  useEffect(() => {
    if (previewData?.target_platform && previewData.target_platform !== submitMatchPlatform) {
      setSubmitMatchPlatform(previewData.target_platform);
    }
  }, [previewData?.target_platform, submitMatchPlatform]);

  // Fetch metadata snapshots from all sources
  const { data: snapshotsData } = useMetadataSnapshots(id, {
    enabled: !!song,
  });
  const fullEnrichment = useFullEnrichment();

  // Set default source when snapshots load
  useEffect(() => {
    if (snapshotsData?.snapshots?.length && !activeMetadataSource) {
      // Default to highest confidence source
      const sorted = [...snapshotsData.snapshots].sort((a, b) => b.confidence - a.confidence);
      setActiveMetadataSource(sorted[0].source);
    }
  }, [snapshotsData, activeMetadataSource]);

  // Build synthetic matches from metadata source snapshots (deezer, spotify, etc.)
  const metadataSourceMatches = useMemo(() => {
    if (!snapshotsData?.snapshots) return [];
    return buildMetadataSourceMatches(
      snapshotsData.snapshots.map((s) => ({
        id: s.id,
        source: s.source,
        confidence: s.confidence,
        data: s.data as Record<string, unknown>,
      })),
      id
    );
  }, [snapshotsData, id]);

  // Load existing matches or auto-search if none exist
  useEffect(() => {
    // Wait for existing matches query to complete
    if (existingMatchesLoading || !song?.platforms[0]) return;

    // If we have existing matches in the database, use them
    if (existingMatches && existingMatches.length > 0) {
      setMatches((prev) => mergeMatches(existingMatches, prev));
      setMatchesLoaded(true);
      return;
    }

    // No existing matches - auto-trigger search (only once)
    if (!autoSearchTriggered && !matchesLoaded && !findMatchesMutation.isPending) {
      setAutoSearchTriggered(true);
      findMatchesMutation.mutate(
        { sourceUrl: song.platforms[0].url, targetPlatforms: TARGET_PLATFORMS },
        {
          onSuccess: (result) => {
            setMatches((prev) => mergeMatches(prev, result.matches));
            setMatchesLoaded(true);
            queryClient.invalidateQueries({ queryKey: matchKeys.list({ songId: id }) });
          },
          onError: () => {
            setMatchesLoaded(true);
          },
        }
      );
    }
  }, [
    autoSearchTriggered,
    existingMatches,
    existingMatchesLoading,
    findMatchesMutation,
    id,
    matchesLoaded,
    queryClient,
    song,
  ]);

  // Combined matches: audio matches + metadata source matches
  const allMatches = useMemo(() => {
    return mergeMatches(matches, metadataSourceMatches);
  }, [matches, metadataSourceMatches]);

  // Handler to find matches (manual refresh)
  const handleFindMatches = () => {
    if (song && song.platforms[0] && !findMatchesMutation.isPending) {
      findMatchesMutation.mutate(
        { sourceUrl: song.platforms[0].url, targetPlatforms: TARGET_PLATFORMS },
        {
          onSuccess: (result) => {
            setMatches((prev) => mergeMatches(prev, result.matches));
            setMatchesLoaded(true);
            queryClient.invalidateQueries({ queryKey: matchKeys.list({ songId: id }) });
            showSuccess(
              result.matches.length > 0
                ? `Found ${result.matches.length} cross-platform matches`
                : "No new matches found"
            );
          },
          onError: (err) => {
            setMatchesLoaded(true);
            showError(err instanceof Error ? err.message : "Failed to find matches");
          },
        }
      );
    }
  };

  // Handler to submit user match
  const handleSubmitMatch = async () => {
    if (!song?.platforms[0] || !submitMatchUrl.trim()) return;

    try {
      const newMatch = await submitMatchMutation.mutateAsync({
        source_url: song.platforms[0].url,
        target_url: submitMatchUrl.trim(),
        target_platform: submitMatchPlatform,
      });

      // Add to matches list
      setMatches((prev) => mergeMatches(prev, [newMatch]));
      setShowSubmitMatch(false);
      setSubmitMatchUrl("");
      queryClient.invalidateQueries({ queryKey: matchKeys.list({ songId: id }) });
      showSuccess("Match submitted successfully");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to submit match");
    }
  };

  // Handler to verify/reject a match
  const handleVerifyMatch = async (matchId: string, status: "verified" | "rejected") => {
    try {
      await updateMatchStatus.mutateAsync({
        matchId,
        data: { status },
      });

      // Update local state
      setMatches((prev) =>
        prev.map((m) =>
          m.id === matchId ? { ...m, status, verified_by_username: user?.username } : m
        )
      );
      showSuccess(status === "verified" ? "Match verified" : "Match rejected");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to update match status");
    }
  };

  const extendedSnapshotsInfo = useMemo(() => {
    const backendSnapshots = snapshotsData?.snapshots || [];
    const syntheticSnapshots = matches.map(match => ({
      id: `synthetic-${match.id || Math.random()}`,
      source: match.target_platform,
      confidence: match.score / 100,
      data: {
        name: match.result.name,
        artist: match.result.artist,
        duration: match.result.duration,
        cover_url: match.result.cover_url,
      },
      fetchedAt: new Date().toISOString(), // Use current time or matching time
    }));

    // For the UI we need typed snapshots
    const combined = [...backendSnapshots, ...syntheticSnapshots] as any[];

    // Build sets of sources
    const allSources = Array.from(new Set([
      ...(snapshotsData?.sources || []),
      ...matches.map(m => m.target_platform)
    ]));

    return {
      snapshots: combined,
      sources: allSources
    };
  }, [snapshotsData, matches]);

  // Get active snapshot data
  const activeSnapshot = useMemo(() => {
    if (!activeMetadataSource) return extendedSnapshotsInfo.snapshots[0] || null;
    return extendedSnapshotsInfo.snapshots.find((s) => s.source === activeMetadataSource) || null;
  }, [extendedSnapshotsInfo, activeMetadataSource]);

  // Merge snapshot metadata with song for display
  const displayMetadata = useMemo(() => {
    if (!song) return null;
    if (!activeSnapshot?.data) return song;

    // Merge snapshot data with song, preferring snapshot values when available
    return {
      ...song,
      genres: activeSnapshot.data.genres || song.genres,
      label: activeSnapshot.data.label || song.label,
      release_date: activeSnapshot.data.release_date || song.release_date,
      year: activeSnapshot.data.year || song.year,
      // Audio features from snapshot if available
      audio_features: song.audio_features
        ? {
            ...song.audio_features,
            bpm: activeSnapshot.data.bpm ?? song.audio_features.bpm,
            energy: activeSnapshot.data.energy ?? song.audio_features.energy,
            danceability: activeSnapshot.data.danceability ?? song.audio_features.danceability,
            valence: activeSnapshot.data.valence ?? song.audio_features.valence,
          }
        : song.audio_features,
    };
  }, [song, activeSnapshot]);

  // Report submission handler
  const handleReportSubmit = async (report: CreateMetadataReportRequest) => {
    await createReportMutation.mutateAsync(report);
  };

  // Fields available for reporting
  const reportableFields = useMemo(() => {
    if (!song) return [];
    return [
      { name: "name", label: "Song Name", currentValue: song.name },
      { name: "artist", label: "Artist", currentValue: song.artist },
      { name: "album_name", label: "Album", currentValue: song.album_name || "" },
      { name: "year", label: "Year", currentValue: String(song.year || "") },
      { name: "release_date", label: "Release Date", currentValue: song.release_date || "" },
      { name: "label", label: "Record Label", currentValue: song.label || "" },
      { name: "genres", label: "Genres", currentValue: song.genres?.join(", ") || "" },
      { name: "isrc", label: "ISRC", currentValue: song.isrc || "" },
      { name: "track_number", label: "Track Number", currentValue: String(song.track_number || "") },
      { name: "disc_number", label: "Disc Number", currentValue: String(song.disc_number || "") },
    ];
  }, [song]);

  const handleDownload = async (match?: Match) => {
    if (!features.canDownload || !song || !song.platforms[0]) {
      navigate({ to: "/queue" });
      return;
    }

    const matchToUse = match || matches[0];
    if (matchToUse) {
      addItem(
        {
          platform: song.platforms[0].platform,
          platform_id: song.platforms[0].platform_id,
          url: song.platforms[0].url,
          name: song.name,
          artists: song.artists,
          artist: song.artist,
          album_name: song.album_name,
          duration: song.duration,
          isrc: song.isrc,
          cover_url: song.cover_url,
        },
        matchToUse
      );
      navigate({ to: "/queue" });
    }
  };

  // Convert lyrics response to component format
  const lyrics = lyricsData && hasLyrics(lyricsData) ? toLyrics(lyricsData) : null;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading track...</p>
      </div>
    );
  }

  if (error || !song) {
    return <EntityErrorCard entityType="song" error={error ?? null} entityId={id} />;
  }

  // Platforms for the grid
  const platformsForGrid = song.platforms;

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Hero Section */}
      <div className="relative">
        {/* Background blur from cover */}
        {song.cover_url && (
          <div className="absolute inset-0 -z-10 overflow-hidden rounded-3xl">
            <img
              src={song.cover_url}
              alt=""
              className="w-full h-full object-cover blur-3xl opacity-20 scale-110"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-bg-chassis/50 to-bg-chassis" />
          </div>
        )}

        <div className="flex flex-col lg:flex-row gap-8 p-6 lg:p-8">
          {/* Cover Art - Large */}
          <div className="shrink-0 mx-auto lg:mx-0">
            <CoverArt
              src={song.cover_url}
              alt={song.name}
              size="hero"
              className="shadow-2xl shadow-black/50"
            />
          </div>

          {/* Song Info */}
          <div className="flex-1 space-y-6 text-center lg:text-left">
            {/* Title and Artist */}
            <div className="space-y-3">
              <div className="flex items-center justify-center lg:justify-start gap-2 flex-wrap">
                <Badge variant="muted" size="sm">Track</Badge>
                {song.explicit && (
                  <Badge variant="warning" size="sm">Explicit</Badge>
                )}
                {song.track_number && song.disc_number && song.disc_number > 1 && (
                  <Badge variant="muted" size="sm">
                    Disc {song.disc_number}, Track {song.track_number}
                  </Badge>
                )}
                {song.track_number && (!song.disc_number || song.disc_number === 1) && (
                  <Badge variant="muted" size="sm">
                    Track {song.track_number}
                  </Badge>
                )}
              </div>
              <h1 className="text-4xl lg:text-5xl font-black tracking-tight text-zinc-50">
                {song.name}
              </h1>
              {song.artist_id ? (
                <Link
                  to="/artist/$id"
                  params={{ id: song.artist_id }}
                  className="text-xl lg:text-2xl text-zinc-400 hover:text-accent-needle transition-colors"
                >
                  {song.artist}
                </Link>
              ) : (
                <p className="text-xl lg:text-2xl text-zinc-400">
                  {song.artist}
                </p>
              )}
            </div>

            {/* Quick Stats */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 text-sm">
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300 font-mono">
                {formatDuration(song.duration)}
              </span>
              {song.album_name && (
                <Link
                  to="/album/$id"
                  params={{ id: song.album_id || "" }}
                  className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300 hover:border-accent-needle/50 hover:text-accent-needle transition-colors"
                >
                  {song.album_name}
                </Link>
              )}
              {song.release_date ? (
                <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400">
                  {song.release_date}
                </span>
              ) : song.year && (
                <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400">
                  {song.year}
                </span>
              )}
              {song.audio_features?.key !== null && song.audio_features?.key !== undefined && (
                <KeySignatureBadge
                  keyNum={song.audio_features.key}
                  mode={song.audio_features.mode}
                />
              )}
            </div>

            {/* Genres */}
            {song.genres && song.genres.length > 0 && (
              <div className="flex flex-wrap justify-center lg:justify-start gap-2">
                {song.genres.map((genre) => (
                  <Badge key={genre} variant="default">
                    {genre}
                  </Badge>
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-2">
              {features.canDownload && matches.length > 0 && (
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => handleDownload()}
                >
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download Best Match
                </Button>
              )}

              <RefreshMetadataButton
                entityId={id}
                onRefresh={async () => {
                  // Refresh from source platform + fetch all metadata sources
                  await refreshMetadata.mutateAsync(id);
                  await fullEnrichment.mutateAsync(id);
                }}
                size="lg"
              />

              {isAuthenticated && (
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => setShowReportModal(true)}
                >
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Report Issue
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Source Metadata Controls */}
      {extendedSnapshotsInfo.snapshots.length > 0 && (
        <Card variant="bordered" className="overflow-hidden">
          <CardContent className="py-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              {/* Source Selector */}
              <MetadataSourceSelector
                sources={extendedSnapshotsInfo.sources}
                activeSource={activeMetadataSource || ""}
                onSourceChange={setActiveMetadataSource}
                snapshots={extendedSnapshotsInfo.snapshots as any}
                showConfidence={true}
                size="md"
              />

              {/* Compare Sources Button */}
              {extendedSnapshotsInfo.snapshots.length > 1 && (
                <Button
                  variant={showComparison ? "primary" : "outline"}
                  size="sm"
                  onClick={() => setShowComparison(!showComparison)}
                >
                  <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                  </svg>
                  {showComparison ? "Hide Comparison" : "Compare Sources"}
                </Button>
              )}
            </div>

            {/* Active Source Info */}
            {activeSnapshot && (
              <div className="mt-3 pt-3 border-t border-zinc-800/50 flex items-center gap-2 text-xs text-zinc-500">
                <span>Viewing data from</span>
                <span className="font-medium text-zinc-300">{activeMetadataSource}</span>
                <span>•</span>
                <span>Confidence: {Math.round(activeSnapshot.confidence * 100)}%</span>
                <span>•</span>
                <span>Fetched: {new Date((activeSnapshot as any).fetched_at || (activeSnapshot as any).fetchedAt || new Date()).toLocaleDateString()}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Metadata Comparison Table */}
      {showComparison && extendedSnapshotsInfo.snapshots.length > 1 && (
        <MetadataComparisonTable
          snapshots={extendedSnapshotsInfo.snapshots as any}
          showOnlyDifferences={false}
          className="animate-slide-up"
        />
      )}

      {/* Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Matches & Lyrics */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cross-Platform Matches Section */}
          <Card variant="bordered">
            <CardHeader className="border-b border-zinc-800/50">
              <div className="flex items-center justify-between w-full">
                <CardTitle className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                  Cross-Platform Matches
                  {matchesLoaded && <Badge variant="muted" size="sm">{allMatches.length}</Badge>}
                </CardTitle>
                <div className="flex items-center gap-2">
                  {isAuthenticated && matchesLoaded && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowSubmitMatch(!showSubmitMatch)}
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Add Match
                    </Button>
                  )}
                  {matchesLoaded && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleFindMatches}
                      isLoading={findMatchesMutation.isPending}
                      disabled={findMatchesMutation.isPending}
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Refresh
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {/* Submit Match Form */}
              {showSubmitMatch && (
                <div className="p-4 border-b border-zinc-800/50 bg-zinc-900/50">
                  <p className="text-sm text-zinc-400 mb-3">
                    Submit a match from another platform. Matches will be reviewed before becoming verified.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <select
                      value={submitMatchPlatform}
                      onChange={(e) => setSubmitMatchPlatform(e.target.value)}
                      className="px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-sm text-zinc-200 focus:outline-none focus:border-accent-needle"
                    >
                      <option value="youtube">YouTube</option>
                      <option value="youtube_music">YouTube Music</option>
                      <option value="soundcloud">SoundCloud</option>
                      <option value="bandcamp">Bandcamp</option>
                      <option value="piped">Piped</option>
                      <option value="spotify">Spotify</option>
                      <option value="deezer">Deezer</option>
                      <option value="apple_music">Apple Music</option>
                      <option value="tidal">TIDAL</option>
                    </select>
                    <input
                      type="url"
                      placeholder="Paste URL from the platform..."
                      value={submitMatchUrl}
                      onChange={(e) => setSubmitMatchUrl(e.target.value)}
                      className="flex-1 px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-accent-needle"
                    />
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleSubmitMatch}
                      disabled={!submitMatchUrl.trim() || submitMatchMutation.isPending}
                      isLoading={submitMatchMutation.isPending}
                    >
                      Submit
                    </Button>
                  </div>
                  {previewLoading && (
                    <p className="text-xs text-zinc-500 mt-2">Fetching link preview...</p>
                  )}
                  {!previewLoading && previewData?.result && submitMatchUrl.trim() && (
                    <div className="mt-3 p-3 rounded-lg border border-zinc-800 bg-zinc-900/70">
                      <p className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                        Link preview ({previewData.target_platform.replace("_", " ")})
                      </p>
                      <p className="text-sm text-zinc-200 font-medium truncate">
                        {previewData.result.name}
                      </p>
                      <p className="text-xs text-zinc-400 truncate">
                        {previewData.result.artist}
                      </p>
                      {previewData.result.description && (
                        <p className="text-xs text-zinc-500 truncate mt-1">
                          {previewData.result.description}
                        </p>
                      )}
                    </div>
                  )}
                  {!previewLoading && previewError && submitMatchUrl.trim() && (
                    <p className="text-xs text-zinc-500 mt-2">
                      Could not preview this link yet. You can still submit it.
                    </p>
                  )}
                  {submitMatchMutation.isError && (
                    <p className="text-sm text-accent-peak mt-2">
                      Failed to submit match. Please check the URL and try again.
                    </p>
                  )}
                </div>
              )}

              {/* Loading state - either loading existing or searching */}
              {(existingMatchesLoading || findMatchesMutation.isPending) && !matchesLoaded && (
                <div className="flex items-center justify-center py-12">
                  <Spinner size="md" />
                  <span className="ml-3 text-zinc-400">
                    {existingMatchesLoading ? "Loading matches..." : "Searching for matches..."}
                  </span>
                </div>
              )}

              {/* Matches loaded */}
              {matchesLoaded && (
                <>
                  {allMatches.length > 0 ? (
                    <div className="divide-y divide-zinc-800/50">
                      {allMatches.map((match, index) => (
                        <MatchRow
                          key={match.id || `${match.target_platform}-${match.target_url}`}
                          match={match}
                          index={index}
                          canVerify={!!canVerifyMatches}
                          canDownload={features.canDownload && match.match_type !== "metadata"}
                          isSelfHosted={features.isSelfHosted}
                          onDownload={() => handleDownload(match)}
                          onVerify={(status) => match.id && !match.id.startsWith("metadata-") && handleVerifyMatch(match.id, status)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="py-12 text-center">
                      <p className="text-zinc-500">No matches found</p>
                      <p className="text-sm text-zinc-600 mt-1">
                        {isAuthenticated
                          ? "Know a match? Click \"Add Match\" to contribute!"
                          : "Log in to submit a match yourself"
                        }
                      </p>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Lyrics Section */}
          <Card variant="bordered" className="overflow-hidden">
            <CardHeader className="border-b border-zinc-800/50">
              <CardTitle className="flex items-center gap-2">
                <svg className="w-5 h-5 text-accent-cool" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Lyrics
                {allLyricsData && allLyricsData.lyrics.length > 1 && (
                  <Badge variant="muted" size="sm">
                    {allLyricsData.lyrics.length} sources
                  </Badge>
                )}
              </CardTitle>
              <div className="flex items-center gap-2">
                {isAuthenticated && (
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => setShowSubmitLyrics(true)}
                  >
                    Add Lyrics
                  </Button>
                )}
                {song && (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={fetchingAllLyrics}
                    onClick={async () => {
                      setFetchingAllLyrics(true);
                      try {
                        await fetchAllLyrics(id);
                        queryClient.invalidateQueries({ queryKey: [...entityKeys.song(id), "all-lyrics"] });
                        showSuccess("Fetched lyrics from all sources");
                      } catch {
                        showError("Failed to fetch lyrics");
                      } finally {
                        setFetchingAllLyrics(false);
                      }
                    }}
                  >
                    {fetchingAllLyrics ? (
                      <Spinner size="sm" />
                    ) : (
                      "Fetch All Sources"
                    )}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {(lyricsLoading || allLyricsLoading) ? (
                <div className="flex items-center justify-center py-12">
                  <Spinner size="md" />
                </div>
              ) : allLyricsData && allLyricsData.lyrics.length > 0 ? (
                // Use multi-source display when multiple sources available
                <MultiSourceLyricsDisplay
                  lyricsSources={allLyricsData.lyrics}
                  activeSource={activeLyricsSource || undefined}
                  onSourceChange={setActiveLyricsSource}
                  maxHeight="400px"
                />
              ) : lyrics ? (
                // Fallback to single-source display
                <LyricsDisplay
                  lyrics={lyrics}
                  maxHeight="400px"
                />
              ) : (
                <div className="py-12 text-center">
                  <p className="text-zinc-500">No lyrics available</p>
                  <p className="text-sm text-zinc-600 mt-1">
                    Lyrics couldn't be found for this track
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Metadata & Links */}
        <div className="space-y-6">
          {/* Platform Links */}
          {(!matchesLoaded || allMatches.length === 0) && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="text-base">Listen On</CardTitle>
              </CardHeader>
              <CardContent>
                <PlatformLinksGrid platforms={platformsForGrid} />
              </CardContent>
            </Card>
          )}

          {/* Audio Features Panel */}
          {displayMetadata?.audio_features && (
            <AudioFeaturesPanel
              features={displayMetadata.audio_features}
              expanded={showAllFeatures}
              onToggleExpand={() => setShowAllFeatures(!showAllFeatures)}
            />
          )}

          {/* Metadata */}
          <MetadataPanel
            title="Track Details"
            defaultOpen={true}
          >
            <div className="space-y-3">
              <MetadataField label="Title" value={displayMetadata?.name || song.name} />
              <MetadataField label="Artist" value={displayMetadata?.artist || song.artist} />
              {(displayMetadata?.album_name || song.album_name) && (
                <MetadataField label="Album" value={displayMetadata?.album_name || song.album_name || ""} />
              )}
              <MetadataField label="Duration" value={<span className="font-mono">{formatDuration(song.duration)}</span>} />
              {(displayMetadata?.release_date || song.release_date) && (
                <MetadataField label="Release Date" value={displayMetadata?.release_date || song.release_date || ""} />
              )}
              {!(displayMetadata?.release_date || song.release_date) && (displayMetadata?.year || song.year) && (
                <MetadataField label="Year" value={String(displayMetadata?.year || song.year)} />
              )}
              {(displayMetadata?.label || song.label) && (
                <MetadataField label="Label" value={displayMetadata?.label || song.label || ""} />
              )}
              {((displayMetadata?.genres && displayMetadata.genres.length > 0) || (song.genres && song.genres.length > 0)) && (
                <MetadataField
                  label="Genres"
                  value={(displayMetadata?.genres || song.genres)?.join(", ") || ""}
                />
              )}
              {song.popularity !== null && song.popularity !== undefined && (
                <MetadataField label="Popularity" value={`${song.popularity}%`} />
              )}
              {/* Show source indicator when viewing non-primary source */}
              {activeMetadataSource && activeMetadataSource !== "spotify" && (
                <div className="pt-2 mt-2 border-t border-zinc-800/30">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wide">
                    Data from <span className="text-accent-cool">{activeMetadataSource}</span>
                  </p>
                </div>
              )}
            </div>
          </MetadataPanel>

          {/* Copyright & Label Info */}
          {(displayMetadata?.label || song.label || song.copyright_text) && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="text-base flex items-center gap-2">
                  <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Rights Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(displayMetadata?.label || song.label) && (
                  <div>
                    <span className="text-xs text-zinc-500 uppercase tracking-wide">Label</span>
                    <p className="text-sm text-zinc-300 mt-0.5">{displayMetadata?.label || song.label}</p>
                  </div>
                )}
                {song.copyright_text && (
                  <div>
                    <span className="text-xs text-zinc-500 uppercase tracking-wide">Copyright</span>
                    <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{song.copyright_text}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Technical Metadata */}
          <Card variant="bordered">
            <CardHeader
              className="border-b border-zinc-800/50 cursor-pointer hover:bg-zinc-800/20 transition-colors"
              onClick={() => setShowTechnicalMetadata(!showTechnicalMetadata)}
            >
              <div className="flex items-center justify-between w-full">
                <CardTitle className="text-base flex items-center gap-2">
                  <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  Technical Info
                </CardTitle>
                <svg
                  className={`w-5 h-5 text-zinc-500 transition-transform ${showTechnicalMetadata ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </CardHeader>
            {showTechnicalMetadata && (
              <CardContent className="space-y-3">
                {song.isrc && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-500">ISRC</span>
                    <code className="text-sm font-mono text-accent-cool bg-bg-panel px-2 py-1 rounded">
                      {song.isrc}
                    </code>
                  </div>
                )}
                {song.platforms[0]?.platform_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-500">
                      {song.platforms[0]?.platform} ID
                    </span>
                    <code className="text-sm font-mono text-zinc-400 bg-bg-panel px-2 py-1 rounded truncate max-w-[180px]">
                      {song.platforms[0]?.platform_id}
                    </code>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-500">Internal ID</span>
                  <code className="text-sm font-mono text-zinc-500 bg-bg-panel px-2 py-1 rounded truncate max-w-[180px]">
                    {id}
                  </code>
                </div>
                {song.matches_count !== undefined && song.matches_count > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-500">Matches Found</span>
                    <Badge variant="info" size="sm">{song.matches_count}</Badge>
                  </div>
                )}

                {/* External IDs */}
                {(song.musicbrainz_id || song.discogs_id) && (
                  <div className="pt-3 mt-3 border-t border-zinc-800/50">
                    <p className="text-xs text-zinc-500 uppercase tracking-wide mb-2">External IDs</p>
                    {song.musicbrainz_id && (
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-zinc-500">MusicBrainz</span>
                        <a
                          href={`https://musicbrainz.org/recording/${song.musicbrainz_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-mono text-orange-400 hover:text-orange-300 bg-bg-panel px-2 py-1 rounded truncate max-w-[180px]"
                        >
                          {song.musicbrainz_id.slice(0, 8)}...
                        </a>
                      </div>
                    )}
                    {song.discogs_id && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-zinc-500">Discogs</span>
                        <a
                          href={`https://www.discogs.com/release/${song.discogs_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-mono text-zinc-400 hover:text-zinc-300 bg-bg-panel px-2 py-1 rounded"
                        >
                          {song.discogs_id}
                        </a>
                      </div>
                    )}
                  </div>
                )}

                {/* Field Sources */}
                {song.field_sources && Object.keys(song.field_sources).length > 0 && (
                  <div className="pt-3 mt-3 border-t border-zinc-800/50">
                    <p className="text-xs text-zinc-500 uppercase tracking-wide mb-2">Data Sources</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(song.field_sources).map(([field, source]) => (
                        <span
                          key={field}
                          className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400"
                          title={`${field} from ${source}`}
                        >
                          {field}: <span className="text-accent-cool">{source}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Enriched timestamp */}
                {song.enriched_at && (
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-sm text-zinc-500">Last Enriched</span>
                    <span className="text-xs text-zinc-500">
                      {new Date(song.enriched_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        </div>
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onSubmit={handleReportSubmit}
        entityType="song"
        entityId={id}
        entityName={song.name}
        fields={reportableFields}
      />

      {/* Submit Lyrics Modal */}
      <SubmitLyricsModal
        isOpen={showSubmitLyrics}
        onClose={() => setShowSubmitLyrics(false)}
        onSubmit={(data) => {
          submitLyricsMutation.mutate({ songId: id, ...data }, {
            onSuccess: () => setShowSubmitLyrics(false),
          });
        }}
        isSubmitting={submitLyricsMutation.isPending}
      />
    </div>
  );
}

// Key Signature Badge Component
function KeySignatureBadge({
  keyNum,
  mode,
}: {
  keyNum: number;
  mode: number | null;
}) {
  const keyName = KEY_NAMES[keyNum] || "?";
  const modeName = mode === 1 ? "Major" : mode === 0 ? "Minor" : "";
  const colorClass = KEY_FAMILY_COLORS[keyName] || "bg-zinc-800 text-zinc-300 border-zinc-700";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border font-medium text-sm ${colorClass}`}
      title={`Key: ${keyName} ${modeName}`}
    >
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
      </svg>
      {keyName} {modeName}
    </span>
  );
}

// Comprehensive Audio Features Panel Component
function AudioFeaturesPanel({
  features,
  expanded,
  onToggleExpand,
}: {
  features: AudioFeatures;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  // Primary features always shown
  const primaryFeatures = [
    { key: "bpm", label: "BPM", value: features.bpm, max: 200, displayFn: (v: number) => `${Math.round(v)}` },
    { key: "energy", label: "Energy", value: features.energy !== null ? features.energy * 100 : null, max: 100 },
    { key: "danceability", label: "Danceability", value: features.danceability !== null ? features.danceability * 100 : null, max: 100 },
    { key: "valence", label: "Valence", value: features.valence !== null ? features.valence * 100 : null, max: 100 },
  ];

  // Secondary features shown when expanded
  const secondaryFeatures = [
    { key: "speechiness", label: "Speechiness", value: features.speechiness !== null ? features.speechiness * 100 : null, max: 100 },
    { key: "acousticness", label: "Acousticness", value: features.acousticness !== null ? features.acousticness * 100 : null, max: 100 },
    { key: "instrumentalness", label: "Instrumentalness", value: features.instrumentalness !== null ? features.instrumentalness * 100 : null, max: 100 },
    { key: "liveness", label: "Liveness", value: features.liveness !== null ? features.liveness * 100 : null, max: 100 },
  ];

  // Technical audio features
  const technicalFeatures = [
    { key: "loudness", label: "Loudness", value: features.loudness, displayFn: (v: number) => `${v.toFixed(1)} dB` },
    { key: "time_signature", label: "Time Signature", value: features.time_signature, displayFn: (v: number) => `${v}/4` },
  ];

  const hasSecondaryFeatures = secondaryFeatures.some(f => f.value !== null);
  const hasTechnicalFeatures = technicalFeatures.some(f => f.value !== null);

  return (
    <Card variant="bordered">
      <CardHeader className="border-b border-zinc-800/50">
        <CardTitle className="text-base flex items-center gap-2">
          <svg className="w-4 h-4 text-accent-warm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
          Audio Features
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Primary Features */}
        {primaryFeatures.map((feature) => (
          feature.value !== null && (
            <AudioFeatureBar
              key={feature.key}
              label={feature.label}
              value={feature.value}
              max={feature.max}
              displayValue={feature.displayFn ? feature.displayFn(feature.value) : undefined}
              tooltip={FEATURE_DESCRIPTIONS[feature.key]}
            />
          )
        ))}

        {/* Expandable Secondary Features */}
        {expanded && hasSecondaryFeatures && (
          <>
            <div className="border-t border-zinc-800/50 pt-4 mt-4">
              <p className="text-xs text-zinc-500 uppercase tracking-wide mb-3">Advanced Features</p>
            </div>
            {secondaryFeatures.map((feature) => (
              feature.value !== null && (
                <AudioFeatureBar
                  key={feature.key}
                  label={feature.label}
                  value={feature.value}
                  max={feature.max}
                  tooltip={FEATURE_DESCRIPTIONS[feature.key]}
                />
              )
            ))}
          </>
        )}

        {/* Technical Features */}
        {expanded && hasTechnicalFeatures && (
          <>
            <div className="border-t border-zinc-800/50 pt-4 mt-4">
              <p className="text-xs text-zinc-500 uppercase tracking-wide mb-3">Technical Details</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {technicalFeatures.map((feature) => (
                feature.value !== null && (
                  <div key={feature.key} className="text-center p-3 bg-bg-panel rounded-lg" title={FEATURE_DESCRIPTIONS[feature.key]}>
                    <p className="text-lg font-bold text-zinc-200 font-mono">
                      {feature.displayFn ? feature.displayFn(feature.value) : feature.value}
                    </p>
                    <p className="text-xs text-zinc-500 mt-0.5">{feature.label}</p>
                  </div>
                )
              ))}
            </div>
          </>
        )}

        {/* Toggle Expand Button */}
        {(hasSecondaryFeatures || hasTechnicalFeatures) && (
          <button
            onClick={onToggleExpand}
            className="w-full mt-2 py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors flex items-center justify-center gap-1"
          >
            {expanded ? "Show Less" : "Show All Features"}
            <svg
              className={`w-4 h-4 transition-transform ${expanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </CardContent>
    </Card>
  );
}

// Enhanced Audio Feature Bar Component with tooltip and color coding
function AudioFeatureBar({
  label,
  value,
  max = 100,
  displayValue,
  tooltip,
}: {
  label: string;
  value: number;
  max?: number;
  displayValue?: string;
  tooltip?: string;
}) {
  const percentage = Math.min((value / max) * 100, 100);
  const colorClass = getIntensityColor(percentage);

  return (
    <div className="space-y-1.5 group" title={tooltip}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400 flex items-center gap-1">
          {label}
          {tooltip && (
            <svg className="w-3.5 h-3.5 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </span>
        <span className="font-mono text-zinc-300">
          {displayValue || `${Math.round(percentage)}%`}
        </span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// Match Row Component with voting and verification
function MatchRow({
  match,
  index,
  canVerify,
  canDownload,
  isSelfHosted = false,
  onDownload,
  onVerify,
}: {
  match: Match;
  index: number;
  canVerify: boolean;
  canDownload: boolean;
  isSelfHosted?: boolean;
  onDownload: () => void;
  onVerify: (status: "verified" | "rejected") => void;
}) {
  const { isAuthenticated } = useAuthStore();
  const createVoteMutation = useCreateVote();
  const deleteVoteMutation = useDeleteVote();
  const { data: voteSummary } = useMatchVotes(match.id || "");
  const { success: showSuccess, error: showError } = useToast();
  const isVotePending = createVoteMutation.isPending || deleteVoteMutation.isPending;

  const handleVote = async (type: "up" | "down") => {
    if (!match.id || !isAuthenticated) return;

    try {
      if (voteSummary?.user_vote === type) {
        await deleteVoteMutation.mutateAsync(match.id);
        showSuccess("Vote removed");
        return;
      }

      await createVoteMutation.mutateAsync({
        match_id: match.id,
        vote_type: type,
      });
      showSuccess(type === "up" ? "Upvoted match" : "Downvoted match");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to update vote");
    }
  };

  const isUserSubmitted = match.match_type === "user";
  const isMetadataMatch = match.match_type === "metadata";
  const isPending = match.status === "pending";
  const isVerified = match.status === "verified";
  const isRejected = match.status === "rejected";
  const isDownloadable = isSelfHosted && DOWNLOADABLE_PLATFORMS.has(match.target_platform);

  return (
    <div
      className={`flex items-center gap-4 px-4 py-3 hover:bg-zinc-800/30 transition-colors ${
        index === 0 && isVerified ? "bg-accent-safe/5" : ""
      } ${isRejected ? "opacity-50" : ""}`}
    >
      {/* Rank */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
        index === 0 && isVerified
          ? "bg-accent-safe/20 text-accent-safe"
          : "bg-zinc-800 text-zinc-500"
      }`}>
        #{index + 1}
      </div>

      {/* Match Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge
            variant={match.target_platform === "youtube_music" ? "error" : "muted"}
            size="sm"
          >
            {match.target_platform.replace("_", " ")}
          </Badge>
          {index === 0 && isVerified && (
            <Badge variant="success" size="sm">Best Match</Badge>
          )}
          {isUserSubmitted && (
            <Badge variant="info" size="sm">User Submitted</Badge>
          )}
          {isMetadataMatch && (
            <Badge variant="default" size="sm">Metadata Source</Badge>
          )}
          {isDownloadable && (
            <Badge variant="success" size="sm">
              <svg className="w-3 h-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Downloadable
            </Badge>
          )}
          {isPending && (
            <Badge variant="warning" size="sm">Pending Review</Badge>
          )}
          {isVerified && (
            <Badge variant="success" size="sm">
              <svg className="w-3 h-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Verified
            </Badge>
          )}
          {isRejected && (
            <Badge variant="error" size="sm">Rejected</Badge>
          )}
        </div>
        <p className="font-medium text-zinc-200 truncate mt-1">
          {match.result.name}
        </p>
        <p className="text-sm text-zinc-500 truncate">
          {match.result.artist}
          {match.submitted_by_username && (
            <span className="text-zinc-600"> • by {match.submitted_by_username}</span>
          )}
        </p>
        {match.result.description && (
          <p className="text-xs text-zinc-600 truncate mt-0.5">
            {match.result.description}
          </p>
        )}
      </div>

      {/* Score */}
      <div className="shrink-0">
        <MatchScoreGauge score={match.score} size="sm" />
      </div>

      {/* Voting */}
      {isAuthenticated && match.id && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleVote("up")}
            disabled={isVotePending}
            className={`p-1.5 rounded transition-colors ${
              voteSummary?.user_vote === "up"
                ? "bg-accent-safe/20 text-accent-safe"
                : "text-zinc-500 hover:text-accent-safe hover:bg-zinc-800"
            }`}
            title="Upvote"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <span className={`text-xs font-mono min-w-[24px] text-center ${
            (voteSummary?.upvotes ?? match.upvotes ?? 0) - (voteSummary?.downvotes ?? match.downvotes ?? 0) > 0
              ? "text-accent-safe"
              : (voteSummary?.upvotes ?? match.upvotes ?? 0) - (voteSummary?.downvotes ?? match.downvotes ?? 0) < 0
                ? "text-accent-peak"
                : "text-zinc-500"
          }`}>
            {(voteSummary?.upvotes ?? match.upvotes ?? 0) - (voteSummary?.downvotes ?? match.downvotes ?? 0)}
          </span>
          <button
            onClick={() => handleVote("down")}
            disabled={isVotePending}
            className={`p-1.5 rounded transition-colors ${
              voteSummary?.user_vote === "down"
                ? "bg-accent-peak/20 text-accent-peak"
                : "text-zinc-500 hover:text-accent-peak hover:bg-zinc-800"
            }`}
            title="Downvote"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      )}

      {/* Verification Actions (for admins/mods/high rep users) */}
      {canVerify && isPending && match.id && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => onVerify("verified")}
            className="p-1.5 rounded text-zinc-500 hover:text-accent-safe hover:bg-accent-safe/10 transition-colors"
            title="Verify this match"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </button>
          <button
            onClick={() => onVerify("rejected")}
            className="p-1.5 rounded text-zinc-500 hover:text-accent-peak hover:bg-accent-peak/10 transition-colors"
            title="Reject this match"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Link & Download Actions */}
      <div className="flex items-center gap-2">
        <a
          href={match.target_url}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
        {canDownload && !isRejected && (
          <Button
            size="sm"
            variant={index === 0 && isVerified ? "primary" : "secondary"}
            onClick={onDownload}
          >
            Download
          </Button>
        )}
      </div>
    </div>
  );
}
