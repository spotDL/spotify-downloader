import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useInternalSong, useRefreshSongMetadata, useEnrichSongMetadata } from "@/api/entities";
import { useFindMatchesMutation, useLyrics, hasLyrics, toLyrics, useCreateReport } from "@/api";
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
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { Spinner } from "@/components/ui";
import { MatchScoreGauge } from "@/components/ui/match-gauge";
import { LyricsDisplay } from "@/components/ui/lyrics-display";
import { MetadataPanel, MetadataField } from "@/components/ui/metadata-source-badge";
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import { ReportModal } from "@/components/ui/report-modal";
import { useDevConfig } from "@/contexts/DevConfigContext";
import type { Match, AudioFeatures, CreateMetadataReportRequest } from "@/types";

export const Route = createFileRoute("/song/$id")({
  component: SongPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

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
  const { id } = Route.useParams();
  const { data: song, isLoading, error } = useInternalSong(id);
  const { data: lyricsData, isLoading: lyricsLoading } = useLyrics(id, { enabled: !!song });
  const findMatchesMutation = useFindMatchesMutation();
  const createReportMutation = useCreateReport();
  const refreshMetadata = useRefreshSongMetadata();
  const enrichMetadata = useEnrichSongMetadata();
  const addItem = useQueueStore((state) => state.addItem);
  const { isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();

  const [showReportModal, setShowReportModal] = useState(false);
  const [matches, setMatches] = useState<Match[]>([]);
  const [matchesLoaded, setMatchesLoaded] = useState(false);
  const [showTechnicalMetadata, setShowTechnicalMetadata] = useState(false);
  const [showAllFeatures, setShowAllFeatures] = useState(false);

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

  // Find matches when the page loads
  const handleFindMatches = async () => {
    if (!song || !song.platforms[0]) return;

    try {
      const result = await findMatchesMutation.mutateAsync({
        sourceUrl: song.platforms[0].url,
        targetPlatforms: TARGET_PLATFORMS,
      });
      setMatches(result.matches);
      setMatchesLoaded(true);
    } catch (err) {
      console.error("Failed to find matches:", err);
      setMatchesLoaded(true);
    }
  };

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

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-accent-peak">Failed to load track</p>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
          <Link to="/" className="text-accent-needle hover:underline mt-4 inline-block">
            Back to home
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (!song) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Track not found</p>
          <Link to="/" className="text-accent-needle hover:underline mt-4 inline-block">
            Back to home
          </Link>
        </CardContent>
      </Card>
    );
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
              {features.canDownload && (
                <>
                  {!matchesLoaded ? (
                    <Button
                      variant="primary"
                      size="lg"
                      onClick={handleFindMatches}
                      isLoading={findMatchesMutation.isPending}
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      Find Matches
                    </Button>
                  ) : matches.length > 0 ? (
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
                  ) : (
                    <Button variant="secondary" size="lg" disabled>
                      No Matches Found
                    </Button>
                  )}
                </>
              )}

              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate({ to: "/matching", search: { url: song.platforms[0]?.url } })}
              >
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                Match Manually
              </Button>

              <RefreshMetadataButton
                entityId={id}
                onRefresh={async () => {
                  await refreshMetadata.mutateAsync(id);
                }}
                onEnrich={async () => {
                  await enrichMetadata.mutateAsync(id);
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

      {/* Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Lyrics & Matches */}
        <div className="lg:col-span-2 space-y-6">
          {/* Lyrics Section */}
          <Card variant="bordered" className="overflow-hidden">
            <CardHeader className="border-b border-zinc-800/50">
              <CardTitle className="flex items-center gap-2">
                <svg className="w-5 h-5 text-accent-cool" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Lyrics
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {lyricsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Spinner size="md" />
                </div>
              ) : lyrics ? (
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

          {/* Matches Section */}
          {matchesLoaded && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                  Cross-Platform Matches
                  <Badge variant="muted" size="sm">{matches.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {matches.length > 0 ? (
                  <div className="divide-y divide-zinc-800/50">
                    {matches.slice(0, 5).map((match, index) => (
                      <div
                        key={`${match.target_platform}-${match.target_url}`}
                        className={`flex items-center gap-4 px-4 py-3 hover:bg-zinc-800/30 transition-colors ${
                          index === 0 ? "bg-accent-safe/5" : ""
                        }`}
                      >
                        {/* Rank */}
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                          index === 0
                            ? "bg-accent-safe/20 text-accent-safe"
                            : "bg-zinc-800 text-zinc-500"
                        }`}>
                          #{index + 1}
                        </div>

                        {/* Match Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={match.target_platform === "youtube_music" ? "error" : "muted"}
                              size="sm"
                            >
                              {match.target_platform.replace("_", " ")}
                            </Badge>
                            {index === 0 && (
                              <Badge variant="success" size="sm">Best Match</Badge>
                            )}
                          </div>
                          <p className="font-medium text-zinc-200 truncate mt-1">
                            {match.result.name}
                          </p>
                          <p className="text-sm text-zinc-500 truncate">
                            {match.result.artist}
                          </p>
                        </div>

                        {/* Score */}
                        <div className="shrink-0">
                          <MatchScoreGauge score={match.score} size="sm" />
                        </div>

                        {/* Actions */}
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
                          {features.canDownload && (
                            <Button
                              size="sm"
                              variant={index === 0 ? "primary" : "secondary"}
                              onClick={() => handleDownload(match)}
                            >
                              Download
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center">
                    <p className="text-zinc-500">No matches found</p>
                    <p className="text-sm text-zinc-600 mt-1">
                      Try matching manually for better results
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Metadata & Links */}
        <div className="space-y-6">
          {/* Platform Links */}
          <Card variant="bordered">
            <CardHeader className="border-b border-zinc-800/50">
              <CardTitle className="text-base">Listen On</CardTitle>
            </CardHeader>
            <CardContent>
              <PlatformLinksGrid platforms={platformsForGrid} />
            </CardContent>
          </Card>

          {/* Audio Features Panel */}
          {song.audio_features && (
            <AudioFeaturesPanel
              features={song.audio_features}
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
              <MetadataField label="Title" value={song.name} />
              <MetadataField label="Artist" value={song.artist} />
              {song.album_name && (
                <MetadataField label="Album" value={song.album_name} />
              )}
              <MetadataField label="Duration" value={<span className="font-mono">{formatDuration(song.duration)}</span>} />
              {song.release_date && (
                <MetadataField label="Release Date" value={song.release_date} />
              )}
              {!song.release_date && song.year && (
                <MetadataField label="Year" value={String(song.year)} />
              )}
              {song.label && (
                <MetadataField label="Label" value={song.label} />
              )}
              {song.genres && song.genres.length > 0 && (
                <MetadataField
                  label="Genres"
                  value={song.genres.join(", ")}
                />
              )}
              {song.popularity !== null && song.popularity !== undefined && (
                <MetadataField label="Popularity" value={`${song.popularity}%`} />
              )}
            </div>
          </MetadataPanel>

          {/* Copyright & Label Info */}
          {(song.label || song.copyright_text) && (
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
                {song.label && (
                  <div>
                    <span className="text-xs text-zinc-500 uppercase tracking-wide">Label</span>
                    <p className="text-sm text-zinc-300 mt-0.5">{song.label}</p>
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
