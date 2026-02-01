import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useInternalArtist, useRefreshArtistMetadata } from "@/api/entities";
import { useFindMatchesMutation, useCreateReport } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { useAuthStore } from "@/stores/auth";
import {
  Card,
  CardContent,
  Badge,
  Button,
  RefreshMetadataButton,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { Spinner } from "@/components/ui";
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import { ReportModal } from "@/components/ui/report-modal";
import { useDevConfig } from "@/contexts/DevConfigContext";
import { clsx } from "clsx";
import type { InternalSong, ArtistSummary, AlbumSummary, CreateMetadataReportRequest, EnhancedArtist } from "@/types";

// Page size for track pagination
const TRACKS_PER_PAGE = 50;

export const Route = createFileRoute("/artist/$id")({
  component: ArtistPage,
});

// Loading state component
function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-4">
      <Spinner size="lg" />
      <p className="text-zinc-500">Loading artist...</p>
    </div>
  );
}

// Error state component
function ErrorState({ error }: { error: Error }) {
  return (
    <div className="max-w-md mx-auto py-20">
      <Card variant="bordered" className="border-red-900/50 bg-red-950/10">
        <CardContent className="py-10 text-center">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-red-400 font-medium">Failed to load artist</p>
          <p className="text-sm text-zinc-500 mt-2">{error.message}</p>
          <Link to="/" className="inline-block mt-6">
            <Button variant="outline">Back to home</Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

type AlbumTypeFilter = "all" | "album" | "single" | "ep" | "compilation";

const ALBUM_TYPE_LABELS: Record<AlbumTypeFilter, string> = {
  all: "All",
  album: "Albums",
  single: "Singles",
  ep: "EPs",
  compilation: "Compilations",
};

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
  return num.toString();
}

// Expandable bio
function ExpandableBio({ bio }: { bio: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const CHAR_LIMIT = 280;
  const shouldTruncate = bio.length > CHAR_LIMIT;
  const displayText = isExpanded || !shouldTruncate ? bio : bio.slice(0, CHAR_LIMIT).trim() + "...";

  return (
    <div className="relative">
      <p className="text-zinc-400 leading-relaxed whitespace-pre-line text-sm">{displayText}</p>
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 text-sm text-emerald-400 hover:text-emerald-300 transition-colors font-medium inline-flex items-center gap-1"
        >
          {isExpanded ? "Show less" : "Read more"}
          <svg className={clsx("w-4 h-4 transition-transform", isExpanded && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      )}
    </div>
  );
}

// Related artists carousel
function RelatedArtistsCarousel({ artists }: { artists: ArtistSummary[] }) {
  if (!artists?.length) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-zinc-100">Related Artists</h2>
        <span className="text-xs text-zinc-500">{artists.length} artists</span>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-3 scrollbar-thin scrollbar-thumb-zinc-700 -mx-1 px-1">
        {artists.map((artist) => (
          <Link
            key={artist.id}
            to="/artist/$id"
            params={{ id: artist.id }}
            className="group flex-shrink-0 w-28"
          >
            <div className="space-y-2 text-center p-2 rounded-lg hover:bg-zinc-800/40 transition-colors">
              <CoverArt
                src={artist.image_url}
                alt={artist.name}
                size="md"
                shape="circle"
                fallbackIcon="artist"
                className="mx-auto ring-1 ring-zinc-800 group-hover:ring-emerald-500/50 transition-all"
              />
              <p className="font-medium text-zinc-300 truncate text-xs group-hover:text-emerald-400 transition-colors">
                {artist.name}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

// Stat pill component
function StatPill({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="flex items-center gap-2 bg-zinc-800/60 px-3 py-1.5 rounded-full">
      <span className="text-sm font-semibold text-zinc-100">{value}</span>
      <span className="text-xs text-zinc-500">{label}</span>
    </div>
  );
}

// Album type filter tabs
function DiscographyTabs({
  activeFilter,
  onFilterChange,
  albumCounts
}: {
  activeFilter: AlbumTypeFilter;
  onFilterChange: (filter: AlbumTypeFilter) => void;
  albumCounts: Record<AlbumTypeFilter, number>;
}) {
  const filters: AlbumTypeFilter[] = ["all", "album", "single", "ep", "compilation"];
  const availableFilters = filters.filter(f => f === "all" || albumCounts[f] > 0);
  if (availableFilters.length <= 2) return null;

  return (
    <div className="flex gap-1.5 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
      {availableFilters.map((filter) => (
        <button
          key={filter}
          onClick={() => onFilterChange(filter)}
          className={clsx(
            "px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap",
            activeFilter === filter
              ? "bg-zinc-100 text-zinc-900"
              : "bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          )}
        >
          {ALBUM_TYPE_LABELS[filter]}
          {filter !== "all" && <span className="ml-1 opacity-60">{albumCounts[filter]}</span>}
        </button>
      ))}
    </div>
  );
}

// Album card
function AlbumCard({ album }: { album: AlbumSummary & { album_type?: string } }) {
  return (
    <Link to="/album/$id" params={{ id: album.id }} className="group block">
      <div className="relative rounded-lg overflow-hidden bg-zinc-900/50 border border-zinc-800/50 hover:border-zinc-700/50 transition-all">
        <div className="relative aspect-square">
          <CoverArt
            src={album.cover_url}
            alt={album.name}
            size="2xl"
            fallbackIcon="album"
            className="!rounded-none w-full h-full group-hover:scale-105 transition-transform duration-300"
          />
          {album.year && (
            <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-black/70 backdrop-blur-sm text-[10px] font-mono text-zinc-300">
              {album.year}
            </div>
          )}
          {album.album_type && album.album_type !== "album" && (
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-emerald-500/90 text-[10px] font-semibold text-black capitalize">
              {album.album_type}
            </div>
          )}
        </div>
        <div className="p-3">
          <p className="font-medium text-zinc-200 truncate text-sm group-hover:text-emerald-400 transition-colors">
            {album.name}
          </p>
          <p className="text-xs text-zinc-500 mt-0.5">{album.total_tracks || "?"} tracks</p>
        </div>
      </div>
    </Link>
  );
}

// Paginated track list
function PaginatedTrackList({
  songs,
  onDownload,
  canDownload,
  isDownloading
}: {
  songs: InternalSong[];
  onDownload: (song: InternalSong) => void;
  canDownload: boolean;
  isDownloading: boolean;
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = Math.ceil(songs.length / TRACKS_PER_PAGE);

  const paginatedSongs = useMemo(() => {
    const start = (currentPage - 1) * TRACKS_PER_PAGE;
    return songs.slice(start, start + TRACKS_PER_PAGE);
  }, [songs, currentPage]);

  const startIndex = (currentPage - 1) * TRACKS_PER_PAGE;

  return (
    <div className="space-y-3">
      {/* Track list */}
      <div className="rounded-xl bg-zinc-900/30 border border-zinc-800/50 overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[40px_48px_1fr_60px_40px] gap-3 px-3 py-2 border-b border-zinc-800/50 text-[10px] text-zinc-500 uppercase tracking-wider font-medium">
          <span className="text-center">#</span>
          <span />
          <span>Title</span>
          <span className="text-right">Time</span>
          {canDownload && <span />}
        </div>

        {/* Tracks */}
        <div>
          {paginatedSongs.map((song, index) => (
            <div
              key={song.id}
              className="grid grid-cols-[40px_48px_1fr_60px_40px] gap-3 px-3 py-2 hover:bg-zinc-800/40 transition-colors group items-center"
            >
              <span className="text-center text-xs font-mono text-zinc-600 group-hover:text-zinc-400">
                {String(startIndex + index + 1).padStart(2, "0")}
              </span>
              <Link to="/song/$id" params={{ id: song.id }}>
                <CoverArt src={song.cover_url} alt={song.name} size="xs" fallbackIcon="track" />
              </Link>
              <div className="min-w-0">
                <Link
                  to="/song/$id"
                  params={{ id: song.id }}
                  className="font-medium text-zinc-200 hover:text-emerald-400 transition-colors truncate block text-sm"
                >
                  {song.name}
                </Link>
                {song.album_name && (
                  <p className="text-xs text-zinc-500 truncate">{song.album_name}</p>
                )}
              </div>
              <span className="text-xs font-mono text-zinc-500 text-right tabular-nums">
                {formatDuration(song.duration)}
              </span>
              {canDownload && (
                <button
                  onClick={() => onDownload(song)}
                  disabled={isDownloading}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-zinc-700/50 text-zinc-400 hover:text-zinc-200 disabled:opacity-50"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2">
          <span className="text-xs text-zinc-500">
            Showing {startIndex + 1}-{Math.min(startIndex + TRACKS_PER_PAGE, songs.length)} of {songs.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span className="text-xs text-zinc-400 px-2">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ArtistPage() {
  const navigate = useNavigate();
  const { id } = Route.useParams();
  const { data: artist, isLoading, error } = useInternalArtist(id);
  const findMatchesMutation = useFindMatchesMutation();
  const refreshMetadata = useRefreshArtistMetadata();
  const { addItem, addBulkItems } = useQueueStore();
  const { isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();

  const [showReportModal, setShowReportModal] = useState(false);
  const [albumTypeFilter, setAlbumTypeFilter] = useState<AlbumTypeFilter>("all");
  const createReportMutation = useCreateReport();

  // Album counts by type
  const albumCounts = useMemo(() => {
    const counts: Record<AlbumTypeFilter, number> = { all: 0, album: 0, single: 0, ep: 0, compilation: 0 };
    if (!artist?.albums) return counts;
    counts.all = artist.albums.length;
    artist.albums.forEach((album) => {
      const type = (album as AlbumSummary & { album_type?: string }).album_type;
      if (type && type in counts) counts[type as AlbumTypeFilter]++;
      else counts.album++;
    });
    return counts;
  }, [artist?.albums]);

  // Filter albums
  const filteredAlbums = useMemo(() => {
    if (!artist?.albums) return [];
    if (albumTypeFilter === "all") return artist.albums;
    return artist.albums.filter((album) => {
      const type = (album as AlbumSummary & { album_type?: string }).album_type;
      return type === albumTypeFilter || (!type && albumTypeFilter === "album");
    });
  }, [artist?.albums, albumTypeFilter]);

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
    if (!features.canDownload || !artist?.songs.length) {
      navigate({ to: "/queue" });
      return;
    }
    const songsToAdd = artist.songs
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
        type: "artist",
        name: artist.name,
        url: artist.platforms[0]?.url || "",
      });
      navigate({ to: "/queue" });
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4">
        <Spinner size="lg" />
        <p className="text-zinc-500">Loading artist...</p>
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="max-w-md mx-auto py-20">
        <Card variant="bordered" className="border-red-900/50 bg-red-950/10">
          <CardContent className="py-10 text-center">
            <p className="text-red-400">{error ? "Failed to load artist" : "Artist not found"}</p>
            <Link to="/" className="inline-block mt-6">
              <Button variant="outline">Back to home</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const enhancedArtist = artist as typeof artist & {
    bio?: string | null;
    origin_country?: string | null;
    origin_city?: string | null;
    formed_year?: number | null;
    related_artists?: ArtistSummary[];
    popularity?: number | null;
  };

  const handleReportSubmit = async (report: CreateMetadataReportRequest) => {
    await createReportMutation.mutateAsync(report);
  };

  const reportFields = [
    { name: "name", label: "Artist Name", currentValue: artist.name },
    ...(artist.genres.length > 0 ? [{ name: "genres", label: "Genres", currentValue: artist.genres.join(", ") }] : []),
    ...(enhancedArtist.bio ? [{ name: "bio", label: "Biography", currentValue: enhancedArtist.bio }] : []),
    ...(enhancedArtist.origin_country ? [{ name: "origin_country", label: "Country", currentValue: enhancedArtist.origin_country }] : []),
  ];

  return (
    <div className="min-h-screen pb-10">
      {/* Compact Header */}
      <div className="relative -mx-6 -mt-6 lg:-mx-8 lg:-mt-8 overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          {artist.image_url && (
            <>
              <img src={artist.image_url} alt="" className="w-full h-full object-cover blur-2xl opacity-30 scale-125" />
              <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0c0c0e]/90 to-[#0c0c0e]" />
            </>
          )}
        </div>

        {/* Content */}
        <div className="relative px-6 py-8 lg:px-8 lg:py-10">
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center gap-6">
              {/* Compact Avatar */}
              <div className="relative flex-shrink-0">
                <div className="absolute -inset-0.5 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-full opacity-40 blur-md" />
                <CoverArt
                  src={artist.image_url}
                  alt={artist.name}
                  size="xl"
                  shape="circle"
                  fallbackIcon="artist"
                  className="relative ring-2 ring-zinc-900/80 shadow-xl"
                />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="muted" size="sm" className="bg-zinc-800/80">Artist</Badge>
                  {enhancedArtist.origin_country && (
                    <span className="text-xs text-zinc-500">{enhancedArtist.origin_country}</span>
                  )}
                </div>
                <h1 className="text-2xl lg:text-4xl font-black tracking-tight text-white truncate">
                  {artist.name}
                </h1>

                {/* Stats */}
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  {artist.monthly_listeners && (
                    <StatPill value={formatNumber(artist.monthly_listeners)} label="listeners" />
                  )}
                  <StatPill value={artist.total_songs} label="songs" />
                  <StatPill value={artist.total_albums} label="albums" />
                </div>

                {/* Genres */}
                {artist.genres.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {artist.genres.slice(0, 4).map((genre) => (
                      <span key={genre} className="px-2 py-0.5 text-xs text-zinc-400 bg-zinc-800/50 rounded-full">
                        {genre}
                      </span>
                    ))}
                    {artist.genres.length > 4 && (
                      <span className="px-2 py-0.5 text-xs text-zinc-500 bg-zinc-800/30 rounded-full">
                        +{artist.genres.length - 4}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-2 mt-6">
              {features.canDownload && artist.songs.length > 0 && (
                <Button variant="primary" size="sm" onClick={handleDownloadAll}>
                  <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download All
                </Button>
              )}
              <RefreshMetadataButton entityId={id} onRefresh={async () => { await refreshMetadata.mutateAsync(id); }} size="sm" />
              {isAuthenticated && (
                <Button variant="ghost" size="sm" onClick={() => setShowReportModal(true)}>
                  <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                  </svg>
                  Report
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto mt-8 space-y-10">
        {/* Platform Links */}
        <section>
          <h2 className="text-lg font-semibold text-zinc-100 mb-4">Listen On</h2>
          <PlatformLinksGrid platforms={artist.platforms} showFollowers />
        </section>

        {/* Bio */}
        {enhancedArtist.bio && (
          <section>
            <h2 className="text-lg font-semibold text-zinc-100 mb-3">About</h2>
            <div className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
              <ExpandableBio bio={enhancedArtist.bio} />
            </div>
          </section>
        )}

        {/* Related Artists */}
        {enhancedArtist.related_artists && enhancedArtist.related_artists.length > 0 && (
          <RelatedArtistsCarousel artists={enhancedArtist.related_artists} />
        )}

        {/* Discography */}
        {artist.albums.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-zinc-100">Discography</h2>
              <span className="text-xs text-zinc-500">{artist.albums.length} releases</span>
            </div>
            <DiscographyTabs activeFilter={albumTypeFilter} onFilterChange={setAlbumTypeFilter} albumCounts={albumCounts} />
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3">
              {filteredAlbums.map((album) => (
                <AlbumCard key={album.id} album={album as AlbumSummary & { album_type?: string }} />
              ))}
            </div>
            {filteredAlbums.length === 0 && (
              <div className="text-center py-12 text-zinc-500 text-sm">
                No {ALBUM_TYPE_LABELS[albumTypeFilter].toLowerCase()} found
              </div>
            )}
          </section>
        )}

        {/* All Tracks - Paginated */}
        {artist.songs.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-zinc-100">All Tracks</h2>
              <span className="text-xs text-zinc-500">{artist.songs.length} songs</span>
            </div>
            <PaginatedTrackList
              songs={artist.songs}
              onDownload={handleDownloadTrack}
              canDownload={features.canDownload}
              isDownloading={findMatchesMutation.isPending}
            />
          </section>
        )}
      </div>

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onSubmit={handleReportSubmit}
        entityType="artist"
        entityId={id}
        entityName={artist.name}
        fields={reportFields}
      />
    </div>
  );
}
