import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useInternalPlaylist, useRefreshPlaylistMetadata } from "@/api/entities";
import { useFindMatchesMutation, useCreateReport } from "@/api";
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
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import { ReportModal } from "@/components/ui/report-modal";
import { useDevConfig } from "@/contexts/DevConfigContext";
import type { InternalSong, CreateMetadataReportRequest } from "@/types";

export const Route = createFileRoute("/playlist/$id")({
  component: PlaylistPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function formatTotalDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours} hr ${mins} min`;
  }
  return `${mins} min`;
}

// Sanitize description by stripping HTML tags using regex (safe approach)
function sanitizeDescription(text: string | null): string {
  if (!text) return "";

  // Strip HTML tags using regex pattern
  let sanitized = text.replace(/<[^>]*>/g, "");

  // Decode common HTML entities
  const entities: Record<string, string> = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&nbsp;": " ",
    "&#x27;": "'",
    "&#x2F;": "/",
  };

  for (const [entity, char] of Object.entries(entities)) {
    sanitized = sanitized.replace(new RegExp(entity, "g"), char);
  }

  // Normalize whitespace and trim
  return sanitized.replace(/\s+/g, " ").trim();
}

// Owner badge component
function OwnerBadge({ name }: { name: string }) {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-800/50 border border-zinc-700/50">
      <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
      <span className="text-sm text-zinc-300 font-medium">{name}</span>
      <Badge variant="info" size="sm">Owner</Badge>
    </div>
  );
}

// Description component with rich text support
function PlaylistDescription({ description }: { description: string | null }) {
  const sanitizedText = useMemo(() => sanitizeDescription(description), [description]);

  if (!sanitizedText) return null;

  // Split by multiple spaces or common separators for paragraph-like formatting
  const lines = sanitizedText.split(/(?:\s{2,}|\n+)/).filter(Boolean);

  return (
    <div className="space-y-2">
      {lines.length === 1 ? (
        <p className="text-zinc-400 leading-relaxed">{sanitizedText}</p>
      ) : (
        lines.map((line, index) => (
          <p key={index} className="text-zinc-400 leading-relaxed">
            {line}
          </p>
        ))
      )}
    </div>
  );
}

function PlaylistPage() {
  const navigate = useNavigate();
  const { id } = Route.useParams();
  const { data: playlist, isLoading, error } = useInternalPlaylist(id);
  const findMatchesMutation = useFindMatchesMutation();
  const refreshMetadata = useRefreshPlaylistMetadata();
  const { addItem, addBulkItems } = useQueueStore();
  const { isAuthenticated } = useAuthStore();
  const createReportMutation = useCreateReport();
  const { features } = useDevConfig();
  const { error: showError } = useToast();

  const [showReportModal, setShowReportModal] = useState(false);

  const handleDownloadTrack = async (track: InternalSong) => {
    if (!features.canDownload || !track.platforms[0]) {
      navigate({ to: "/queue" });
      return;
    }

    try {
      const matchResult = await findMatchesMutation.mutateAsync({
        sourceUrl: track.platforms[0].url,
        targetPlatforms: TARGET_PLATFORMS,
      });

      if (matchResult.matches.length > 0) {
        addItem(
          {
            platform: track.platforms[0].platform,
            platform_id: track.platforms[0].platform_id,
            url: track.platforms[0].url,
            name: track.name,
            artists: track.artists,
            artist: track.artist,
            album_name: track.album_name,
            duration: track.duration,
            isrc: track.isrc,
            cover_url: track.cover_url,
          },
          matchResult.matches[0]
        );
        navigate({ to: "/queue" });
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to find matches for this track");
    }
  };

  const handleDownloadAll = async () => {
    if (!features.canDownload || !playlist?.songs.length) {
      navigate({ to: "/queue" });
      return;
    }

    const songsToAdd = playlist.songs
      .filter((song) => song.platforms[0])
      .map((song) => ({
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
      }));

    if (songsToAdd.length > 0 && addBulkItems) {
      addBulkItems(songsToAdd, {
        type: "playlist",
        name: playlist.name,
        url: playlist.platforms[0]?.url || "",
      });
      navigate({ to: "/queue" });
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading playlist...</p>
      </div>
    );
  }

  if (error || !playlist) {
    return <EntityErrorCard entityType="playlist" error={error ?? null} entityId={id} />;
  }

  const totalDuration = playlist.songs.reduce((sum, song) => sum + song.duration, 0);

  // Convert platforms to PlatformLink format
  const platformLinks = playlist.platforms;

  // Handle report submission
  const handleReportSubmit = async (report: CreateMetadataReportRequest) => {
    await createReportMutation.mutateAsync(report);
  };

  // Build report fields based on playlist data
  const reportFields = [
    { name: "name", label: "Playlist Name", currentValue: playlist.name },
    ...(playlist.owner_name ? [{ name: "owner_name", label: "Owner Name", currentValue: playlist.owner_name }] : []),
    ...(playlist.description ? [{ name: "description", label: "Description", currentValue: sanitizeDescription(playlist.description) }] : []),
  ];

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Hero Section */}
      <div className="relative">
        {/* Background blur from cover */}
        {playlist.cover_url && (
          <div className="absolute inset-0 -z-10 overflow-hidden rounded-3xl">
            <img
              src={playlist.cover_url}
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
              src={playlist.cover_url}
              alt={playlist.name}
              size="hero"
              fallbackIcon="playlist"
              className="shadow-2xl shadow-black/50"
            />
          </div>

          {/* Playlist Info */}
          <div className="flex-1 space-y-6 text-center lg:text-left">
            {/* Title and Owner */}
            <div className="space-y-4">
              <div className="flex items-center justify-center lg:justify-start gap-2">
                <Badge variant="muted" size="sm">Playlist</Badge>
              </div>
              <h1 className="text-4xl lg:text-5xl font-black tracking-tight text-zinc-50">
                {playlist.name}
              </h1>

              {/* Owner Badge */}
              {playlist.owner_name && (
                <div className="flex justify-center lg:justify-start">
                  <OwnerBadge name={playlist.owner_name} />
                </div>
              )}
            </div>

            {/* Description */}
            {playlist.description && (
              <div className="max-w-2xl mx-auto lg:mx-0">
                <PlaylistDescription description={playlist.description} />
              </div>
            )}

            {/* Quick Stats */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 text-sm">
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300">
                {playlist.total_tracks} tracks
              </span>
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400 font-mono">
                {formatTotalDuration(totalDuration)}
              </span>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-2">
              {features.canDownload && playlist.songs.length > 0 && (
                <Button variant="primary" size="lg" onClick={handleDownloadAll}>
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download Playlist
                </Button>
              )}

              <RefreshMetadataButton
                entityId={id}
                onRefresh={async () => {
                  await refreshMetadata.mutateAsync(id);
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
        {/* Left Column - Track List */}
        <div className="lg:col-span-2">
          {/* Track List */}
          {playlist.songs.length > 0 && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  Tracks
                </CardTitle>
              </CardHeader>
              <div className="divide-y divide-zinc-800/50">
                {playlist.songs.map((song, index) => (
                  <div
                    key={song.id}
                    className="flex items-center gap-4 px-4 py-3 hover:bg-zinc-800/30 transition-colors group"
                  >
                    {/* Track position number */}
                    <span className="w-8 text-center text-sm font-mono text-zinc-500 tabular-nums">
                      {index + 1}
                    </span>

                    {/* Cover Art Thumbnail */}
                    <Link to="/song/$id" params={{ id: song.id }}>
                      <CoverArt
                        src={song.cover_url}
                        alt={song.name}
                        size="xs"
                        fallbackIcon="track"
                        className="hover:ring-2 ring-accent-needle/50 transition-all"
                      />
                    </Link>

                    {/* Song Info */}
                    <div className="flex-1 min-w-0">
                      <Link
                        to="/song/$id"
                        params={{ id: song.id }}
                        className="font-medium text-zinc-100 hover:text-accent-needle transition-colors truncate block"
                      >
                        {song.name}
                      </Link>
                      <p className="text-sm text-zinc-500 truncate">
                        {song.artist}
                        {song.album_name && (
                          <span className="text-zinc-600"> - {song.album_name}</span>
                        )}
                      </p>
                    </div>

                    {/* Match count indicator */}
                    {song.matches_count !== undefined && song.matches_count > 0 && (
                      <span className="flex items-center gap-1 text-xs text-accent-needle" title={`${song.matches_count} cross-platform matches`}>
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                        </svg>
                        {song.matches_count}
                      </span>
                    )}

                    {/* Duration */}
                    <span className="text-sm font-mono text-zinc-500 tabular-nums">
                      {formatDuration(song.duration)}
                    </span>

                    {/* Download button - visible on hover */}
                    {features.canDownload && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.preventDefault();
                          handleDownloadTrack(song);
                        }}
                        isLoading={findMatchesMutation.isPending}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {playlist.songs.length === 0 && (
            <Card variant="bordered">
              <CardContent className="py-12 text-center">
                <svg className="w-12 h-12 text-zinc-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
                <p className="text-zinc-400">This playlist has no tracks</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Metadata & Links */}
        <div className="space-y-6">
          {/* Platform Links Grid */}
          <Card variant="bordered">
            <CardHeader className="border-b border-zinc-800/50">
              <CardTitle className="text-base">Listen On</CardTitle>
            </CardHeader>
            <CardContent>
              {platformLinks.length > 0 ? (
                <PlatformLinksGrid platforms={platformLinks} showFollowers />
              ) : (
                <p className="text-sm text-zinc-500">No platform links available</p>
              )}
            </CardContent>
          </Card>

          {/* Playlist Stats */}
          <Card variant="bordered">
            <CardContent className="py-4">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-zinc-200">
                    {playlist.total_tracks}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wide">
                    Tracks
                  </p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-zinc-200 font-mono">
                    {formatTotalDuration(totalDuration)}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wide">
                    Duration
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Additional Info */}
          {playlist.owner_name && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="text-base">Created By</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center">
                    <svg className="w-5 h-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-zinc-200">{playlist.owner_name}</p>
                    <p className="text-xs text-zinc-500">Playlist Owner</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onSubmit={handleReportSubmit}
        entityType="playlist"
        entityId={id}
        entityName={playlist.name}
        fields={reportFields}
      />
    </div>
  );
}
