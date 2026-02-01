import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useInternalAlbum, useRefreshAlbumMetadata } from "@/api/entities";
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
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { Spinner } from "@/components/ui";
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import { MetadataPanel, MetadataField } from "@/components/ui/metadata-source-badge";
import { ReportModal } from "@/components/ui/report-modal";
import { useDevConfig } from "@/contexts/DevConfigContext";
import type { InternalSong, CreateMetadataReportRequest } from "@/types";

export const Route = createFileRoute("/album/$id")({
  component: AlbumPage,
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

// Album type badge styling
const ALBUM_TYPE_STYLES: Record<string, { variant: "default" | "success" | "warning" | "error" | "info" | "premium" | "muted"; label: string }> = {
  album: { variant: "info", label: "Album" },
  single: { variant: "warning", label: "Single" },
  ep: { variant: "success", label: "EP" },
  compilation: { variant: "premium", label: "Compilation" },
};

function AlbumPage() {
  const navigate = useNavigate();
  const { id } = Route.useParams();
  const { data: album, isLoading, error } = useInternalAlbum(id);
  const findMatchesMutation = useFindMatchesMutation();
  const createReportMutation = useCreateReport();
  const refreshMetadata = useRefreshAlbumMetadata();
  const { addItem, addBulkItems } = useQueueStore();
  const { isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();

  const [showReportModal, setShowReportModal] = useState(false);
  const [showMetadata, setShowMetadata] = useState(true);

  // Report submission handler
  const handleReportSubmit = async (report: CreateMetadataReportRequest) => {
    await createReportMutation.mutateAsync(report);
  };

  // Fields available for reporting
  const reportableFields = useMemo(() => {
    if (!album) return [];
    return [
      { name: "name", label: "Album Name", currentValue: album.name },
      { name: "artist_name", label: "Artist Name", currentValue: album.artist_name },
      { name: "year", label: "Release Year", currentValue: String(album.year || "") },
      { name: "release_date", label: "Release Date", currentValue: album.release_date || "" },
      { name: "label", label: "Record Label", currentValue: album.label || "" },
      { name: "album_type", label: "Album Type", currentValue: album.album_type || "" },
      { name: "genres", label: "Genres", currentValue: album.genres?.join(", ") || "" },
      { name: "copyright_text", label: "Copyright", currentValue: album.copyright_text || "" },
    ];
  }, [album]);

  // Group songs by disc number
  const discGroups = useMemo(() => {
    if (!album?.songs.length) return [];

    // Check if any songs have disc_number > 1
    const hasMultipleDiscs = album.songs.some((song: any) => song.disc_number && song.disc_number > 1);

    if (!hasMultipleDiscs) {
      // Single disc album - return songs sorted by track number
      const sortedSongs = [...album.songs].sort((a: any, b: any) => {
        const trackA = a.track_number || 0;
        const trackB = b.track_number || 0;
        return trackA - trackB;
      });
      return [{ discNumber: 1, songs: sortedSongs, isMultiDisc: false }];
    }

    // Multi-disc album - group by disc number
    const groups: Record<number, InternalSong[]> = {};
    album.songs.forEach((song: any) => {
      const discNum = song.disc_number || 1;
      if (!groups[discNum]) {
        groups[discNum] = [];
      }
      groups[discNum].push(song);
    });

    // Sort songs within each disc by track number
    return Object.entries(groups)
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([discNum, songs]) => ({
        discNumber: Number(discNum),
        songs: songs.sort((a: any, b: any) => {
          const trackA = a.track_number || 0;
          const trackB = b.track_number || 0;
          return trackA - trackB;
        }),
        isMultiDisc: true,
      }));
  }, [album?.songs]);

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
      console.error("Failed to find matches:", err);
    }
  };

  const handleDownloadAll = async () => {
    if (!features.canDownload || !album?.songs.length) {
      navigate({ to: "/queue" });
      return;
    }

    const songsToAdd = album.songs
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
        type: "album",
        name: album.name,
        url: album.platforms[0]?.url || "",
      });
      navigate({ to: "/queue" });
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading album...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-accent-peak">Failed to load album</p>
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

  if (!album) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Album not found</p>
          <Link to="/" className="text-accent-needle hover:underline mt-4 inline-block">
            Back to home
          </Link>
        </CardContent>
      </Card>
    );
  }

  const totalDuration = album.songs.reduce((sum, song) => sum + song.duration, 0);
  const albumTypeStyle = ALBUM_TYPE_STYLES[album.album_type] || ALBUM_TYPE_STYLES.album;

  // Convert platforms to PlatformInfo format for the grid
  const platformsForGrid = album.platforms;

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Hero Section */}
      <div className="relative">
        {/* Background blur from cover */}
        {album.cover_url && (
          <div className="absolute inset-0 -z-10 overflow-hidden rounded-3xl">
            <img
              src={album.cover_url}
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
              src={album.cover_url}
              alt={album.name}
              size="hero"
              className="shadow-2xl shadow-black/50"
            />
          </div>

          {/* Album Info */}
          <div className="flex-1 space-y-6 text-center lg:text-left">
            {/* Title and Artist */}
            <div className="space-y-3">
              <div className="flex items-center justify-center lg:justify-start gap-2">
                <Badge variant={albumTypeStyle.variant} size="sm" className="font-semibold">
                  {albumTypeStyle.label}
                </Badge>
                {album.popularity !== null && album.popularity !== undefined && album.popularity >= 70 && (
                  <Badge variant="premium" size="sm">
                    Popular
                  </Badge>
                )}
              </div>
              <h1 className="text-4xl lg:text-5xl font-black tracking-tight text-zinc-50">
                {album.name}
              </h1>
              {album.artist_id ? (
                <Link
                  to="/artist/$id"
                  params={{ id: album.artist_id }}
                  className="text-xl text-zinc-400 hover:text-accent-needle transition-colors inline-block"
                >
                  {album.artist_name}
                </Link>
              ) : (
                <p className="text-xl text-zinc-400">{album.artist_name}</p>
              )}
            </div>

            {/* Quick Stats */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 text-sm">
              {album.release_date ? (
                <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300">
                  {formatDate(album.release_date)}
                </span>
              ) : album.year && (
                <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300">
                  {album.year}
                </span>
              )}
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300">
                {album.total_tracks} {album.total_tracks === 1 ? "track" : "tracks"}
              </span>
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400 font-mono">
                {formatTotalDuration(totalDuration)}
              </span>
              {discGroups.length > 1 && (
                <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400">
                  {discGroups.length} discs
                </span>
              )}
            </div>

            {/* Genres */}
            {album.genres && album.genres.length > 0 && (
              <div className="flex flex-wrap justify-center lg:justify-start gap-2">
                {album.genres.map((genre) => (
                  <Badge key={genre} variant="default">
                    {genre}
                  </Badge>
                ))}
              </div>
            )}

            {/* Label */}
            {album.label && (
              <p className="text-sm text-zinc-500">
                <span className="text-zinc-600">Label:</span> {album.label}
              </p>
            )}

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-2">
              {features.canDownload && album.songs.length > 0 && (
                <Button variant="primary" size="lg" onClick={handleDownloadAll}>
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download Album
                </Button>
              )}

              <Button
                variant="outline"
                size="lg"
                onClick={() => setShowMetadata(!showMetadata)}
              >
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {showMetadata ? "Hide Details" : "Show Details"}
              </Button>

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
          {album.songs.length > 0 && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-accent-needle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  Tracks
                  <Badge variant="muted" size="sm">{album.total_tracks}</Badge>
                </CardTitle>
              </CardHeader>
              <div>
                {discGroups.map((group, groupIndex) => (
                  <div key={group.discNumber}>
                    {/* Disc Header (only for multi-disc albums) */}
                    {group.isMultiDisc && (
                      <div className="px-4 py-3 bg-zinc-900/50 border-b border-zinc-800/50">
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="text-sm font-medium text-zinc-400">
                            Disc {group.discNumber}
                          </span>
                          <span className="text-xs text-zinc-600">
                            ({group.songs.length} {group.songs.length === 1 ? "track" : "tracks"})
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Track Rows */}
                    <div className={`divide-y divide-zinc-800/50 ${groupIndex < discGroups.length - 1 ? "border-b border-zinc-700/50" : ""}`}>
                      {group.songs.map((song: any, index: number) => (
                        <div
                          key={song.id}
                          className="flex items-center gap-4 px-4 py-3 hover:bg-zinc-800/30 transition-colors group"
                        >
                          {/* Track number */}
                          <span className="w-8 text-center text-sm font-mono text-zinc-500">
                            {String(song.track_number || index + 1).padStart(2, "0")}
                          </span>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <Link
                              to="/song/$id"
                              params={{ id: song.id }}
                              className="font-medium text-zinc-100 hover:text-accent-needle transition-colors truncate block"
                            >
                              {song.name}
                            </Link>
                            {song.artist !== album.artist_name && (
                              <p className="text-sm text-zinc-500 truncate">
                                {song.artist}
                              </p>
                            )}
                          </div>

                          {/* Explicit badge */}
                          {song.explicit && (
                            <Badge variant="warning" size="sm">E</Badge>
                          )}

                          {/* Duration */}
                          <span className="text-sm font-mono text-zinc-500">
                            {formatDuration(song.duration)}
                          </span>

                          {/* Download button */}
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
                  </div>
                ))}
              </div>
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

          {/* Album Details */}
          {showMetadata && (
            <MetadataPanel
              title="Album Details"
              defaultOpen={true}
            >
              <div className="space-y-3">
                <MetadataField label="Title" value={album.name} />
                <MetadataField label="Artist" value={album.artist_name} />
                <MetadataField label="Type" value={albumTypeStyle.label} />
                {album.release_date && (
                  <MetadataField label="Release Date" value={formatDate(album.release_date)} />
                )}
                {!album.release_date && album.year && (
                  <MetadataField label="Release Year" value={String(album.year)} />
                )}
                {album.label && (
                  <MetadataField label="Label" value={album.label} />
                )}
                <MetadataField label="Tracks" value={String(album.total_tracks)} />
                {discGroups.length > 1 && (
                  <MetadataField label="Discs" value={String(discGroups.length)} />
                )}
                <MetadataField
                  label="Duration"
                  value={<span className="font-mono">{formatTotalDuration(totalDuration)}</span>}
                />
                {album.popularity !== null && album.popularity !== undefined && (
                  <MetadataField label="Popularity" value={`${album.popularity}%`} />
                )}
                {album.genres && album.genres.length > 0 && (
                  <MetadataField
                    label="Genres"
                    value={album.genres.join(", ")}
                  />
                )}
              </div>
            </MetadataPanel>
          )}

          {/* Copyright Info */}
          {showMetadata && album.copyright_text && (
            <Card variant="bordered">
              <CardHeader className="border-b border-zinc-800/50">
                <CardTitle className="text-base flex items-center gap-2">
                  <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Rights Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-zinc-400 leading-relaxed">{album.copyright_text}</p>
              </CardContent>
            </Card>
          )}

          {/* Quick Stats */}
          <Card variant="bordered">
            <CardContent className="py-4">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-zinc-200">
                    {album.total_tracks}
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
              {discGroups.length > 1 && (
                <div className="mt-4 pt-4 border-t border-zinc-800/50 text-center">
                  <p className="text-xl font-bold text-zinc-300">
                    {discGroups.length}
                  </p>
                  <p className="text-xs text-zinc-500 uppercase tracking-wide">
                    Discs
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Album Type Info Card */}
          {album.album_type && album.album_type !== "album" && (
            <Card variant="bordered" className="overflow-hidden">
              <div className={`p-4 ${
                album.album_type === "single" ? "bg-amber-950/20" :
                album.album_type === "ep" ? "bg-emerald-950/20" :
                album.album_type === "compilation" ? "bg-violet-950/20" : ""
              }`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    album.album_type === "single" ? "bg-amber-900/50" :
                    album.album_type === "ep" ? "bg-emerald-900/50" :
                    album.album_type === "compilation" ? "bg-violet-900/50" : "bg-zinc-800"
                  }`}>
                    {album.album_type === "single" && (
                      <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                      </svg>
                    )}
                    {album.album_type === "ep" && (
                      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                    )}
                    {album.album_type === "compilation" && (
                      <svg className="w-5 h-5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-zinc-200">
                      {album.album_type === "single" ? "Single Release" :
                       album.album_type === "ep" ? "Extended Play" :
                       album.album_type === "compilation" ? "Compilation Album" : ""}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {album.album_type === "single" ? "1-3 tracks" :
                       album.album_type === "ep" ? "4-6 tracks" :
                       album.album_type === "compilation" ? "Various artists or greatest hits" : ""}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onSubmit={handleReportSubmit}
        entityType="album"
        entityId={id}
        entityName={album.name}
        fields={reportableFields}
      />
    </div>
  );
}
