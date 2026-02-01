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
import type { InternalSong, ArtistSummary, AlbumSummary, CreateMetadataReportRequest } from "@/types";

export const Route = createFileRoute("/artist/$id")({
  component: ArtistPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

// Album type filter options
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
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(0)}K`;
  }
  return num.toString();
}

// Component for expandable bio section
function ExpandableBio({ bio }: { bio: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const CHAR_LIMIT = 280;
  const shouldTruncate = bio.length > CHAR_LIMIT;

  const displayText = isExpanded || !shouldTruncate
    ? bio
    : bio.slice(0, CHAR_LIMIT).trim() + "...";

  return (
    <div className="relative">
      <p className="text-zinc-400 leading-relaxed whitespace-pre-line text-[15px]">
        {displayText}
      </p>
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 text-sm text-emerald-400 hover:text-emerald-300 transition-colors font-medium inline-flex items-center gap-1"
        >
          {isExpanded ? (
            <>
              Show less
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </>
          ) : (
            <>
              Read more
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </>
          )}
        </button>
      )}
    </div>
  );
}

// Component for related artists carousel
function RelatedArtistsCarousel({ artists }: { artists: ArtistSummary[] }) {
  if (!artists || artists.length === 0) return null;

  return (
    <section className="animate-slide-up" style={{ animationDelay: "0.3s", opacity: 0 }}>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold text-zinc-100 tracking-tight">Related Artists</h2>
        <span className="text-sm text-zinc-500">{artists.length} artists</span>
      </div>
      <div className="relative -mx-2">
        <div className="flex gap-3 overflow-x-auto pb-4 px-2 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent snap-x snap-mandatory">
          {artists.map((artist, index) => (
            <Link
              key={artist.id}
              to="/artist/$id"
              params={{ id: artist.id }}
              className="group flex-shrink-0 w-[140px] snap-start"
              style={{ animationDelay: `${0.4 + index * 0.05}s` }}
            >
              <div className="space-y-3 text-center p-3 rounded-xl hover:bg-zinc-800/30 transition-all duration-300">
                <div className="relative">
                  <CoverArt
                    src={artist.image_url}
                    alt={artist.name}
                    size="lg"
                    shape="circle"
                    fallbackIcon="artist"
                    className="mx-auto ring-2 ring-zinc-800 group-hover:ring-emerald-500/50 transition-all duration-300 group-hover:scale-105"
                  />
                  {/* Subtle glow on hover */}
                  <div className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none bg-gradient-to-t from-emerald-500/10 to-transparent" />
                </div>
                <div>
                  <p className="font-semibold text-zinc-200 truncate group-hover:text-emerald-400 transition-colors text-sm">
                    {artist.name}
                  </p>
                  {artist.genres.length > 0 && (
                    <p className="text-xs text-zinc-500 truncate mt-0.5">
                      {artist.genres.slice(0, 2).join(" · ")}
                    </p>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

// Component for origin info display
function OriginInfo({
  country,
  city,
  formedYear
}: {
  country: string | null;
  city: string | null;
  formedYear: number | null;
}) {
  const parts: string[] = [];

  if (city && country) {
    parts.push(`${city}, ${country}`);
  } else if (country) {
    parts.push(country);
  } else if (city) {
    parts.push(city);
  }

  if (!parts.length && !formedYear) return null;

  return (
    <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
      {parts.length > 0 && (
        <div className="flex items-center gap-2 text-zinc-400 bg-zinc-800/50 px-3 py-1.5 rounded-full">
          <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>{parts[0]}</span>
        </div>
      )}
      {formedYear && (
        <div className="flex items-center gap-2 text-zinc-400 bg-zinc-800/50 px-3 py-1.5 rounded-full">
          <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span>Since {formedYear}</span>
        </div>
      )}
    </div>
  );
}

// Stat card component
function StatCard({ value, label, highlight = false }: { value: string | number; label: string; highlight?: boolean }) {
  return (
    <div className={clsx(
      "text-center px-6 py-4 rounded-xl transition-all duration-300",
      highlight
        ? "bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/20"
        : "bg-zinc-800/40 hover:bg-zinc-800/60"
    )}>
      <p className={clsx(
        "text-2xl font-bold tracking-tight",
        highlight ? "text-emerald-400" : "text-zinc-100"
      )}>
        {value}
      </p>
      <p className="text-xs text-zinc-500 mt-1 uppercase tracking-wider font-medium">{label}</p>
    </div>
  );
}

// Discography filter tabs component
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
    <div className="flex gap-2 mb-6 overflow-x-auto pb-2 -mx-2 px-2">
      {availableFilters.map((filter) => (
        <button
          key={filter}
          onClick={() => onFilterChange(filter)}
          className={clsx(
            "px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 whitespace-nowrap",
            activeFilter === filter
              ? "bg-zinc-100 text-zinc-900 shadow-lg shadow-zinc-100/10"
              : "bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          )}
        >
          {ALBUM_TYPE_LABELS[filter]}
          {filter !== "all" && (
            <span className={clsx(
              "ml-1.5 text-xs",
              activeFilter === filter ? "text-zinc-600" : "text-zinc-600"
            )}>
              {albumCounts[filter]}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// Album card component
function AlbumCard({ album, index }: { album: AlbumSummary & { album_type?: string }; index: number }) {
  return (
    <Link
      to="/album/$id"
      params={{ id: album.id }}
      className="group animate-slide-up block"
      style={{ animationDelay: `${0.1 + index * 0.03}s`, opacity: 0 }}
    >
      <div className="relative rounded-xl overflow-hidden bg-zinc-900/50 border border-zinc-800/50 hover:border-zinc-700/50 transition-all duration-300 hover:shadow-xl hover:shadow-black/20">
        {/* Album Cover */}
        <div className="relative aspect-square overflow-hidden">
          <CoverArt
            src={album.cover_url}
            alt={album.name}
            size="2xl"
            fallbackIcon="album"
            className="!rounded-none w-full h-full group-hover:scale-105 transition-transform duration-500"
          />

          {/* Overlay gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Year Badge - top right */}
          {album.year && (
            <div className="absolute top-3 right-3 px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-sm text-xs font-mono text-zinc-200 border border-zinc-700/50">
              {album.year}
            </div>
          )}

          {/* Album Type Badge - bottom left */}
          {album.album_type && album.album_type !== "album" && (
            <div className="absolute bottom-3 left-3 px-2.5 py-1 rounded-md bg-emerald-500/90 backdrop-blur-sm text-xs font-semibold text-black capitalize">
              {album.album_type}
            </div>
          )}

          {/* Play overlay */}
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <div className="w-12 h-12 rounded-full bg-emerald-500 flex items-center justify-center shadow-xl shadow-emerald-500/30 transform scale-90 group-hover:scale-100 transition-transform duration-300">
              <svg className="w-5 h-5 text-black ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </div>
        </div>

        {/* Album Info */}
        <div className="p-4">
          <p className="font-semibold text-zinc-100 truncate group-hover:text-emerald-400 transition-colors text-[15px]">
            {album.name}
          </p>
          <p className="text-sm text-zinc-500 mt-1">
            {album.total_tracks || "?"} tracks
          </p>
        </div>
      </div>
    </Link>
  );
}

// Track row component
function TrackRow({
  song,
  index,
  onDownload,
  canDownload,
  isDownloading
}: {
  song: InternalSong;
  index: number;
  onDownload: () => void;
  canDownload: boolean;
  isDownloading: boolean;
}) {
  return (
    <div
      className={clsx(
        "flex items-center gap-4 px-4 py-3 rounded-lg hover:bg-zinc-800/50 transition-all duration-200 group",
        "animate-slide-up"
      )}
      style={{ animationDelay: `${0.05 + index * 0.02}s`, opacity: 0 }}
    >
      {/* Track number */}
      <span className="w-8 text-center text-sm font-mono text-zinc-600 group-hover:text-zinc-400 transition-colors">
        {String(index + 1).padStart(2, "0")}
      </span>

      {/* Cover */}
      <Link to="/song/$id" params={{ id: song.id }} className="flex-shrink-0">
        <CoverArt
          src={song.cover_url}
          alt={song.name}
          size="xs"
          fallbackIcon="track"
          className="group-hover:ring-2 ring-zinc-600 transition-all"
        />
      </Link>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <Link
          to="/song/$id"
          params={{ id: song.id }}
          className="font-medium text-zinc-200 hover:text-emerald-400 transition-colors truncate block text-[15px]"
        >
          {song.name}
        </Link>
        {song.album_name && (
          <p className="text-sm text-zinc-500 truncate">{song.album_name}</p>
        )}
      </div>

      {/* Duration */}
      <span className="text-sm font-mono text-zinc-500 tabular-nums">
        {formatDuration(song.duration)}
      </span>

      {/* Download button */}
      {canDownload && (
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.preventDefault();
            onDownload();
          }}
          isLoading={isDownloading}
          className="opacity-0 group-hover:opacity-100 transition-all duration-200 !px-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </Button>
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

  // Calculate album counts by type
  const albumCounts = useMemo(() => {
    const counts: Record<AlbumTypeFilter, number> = {
      all: 0,
      album: 0,
      single: 0,
      ep: 0,
      compilation: 0,
    };

    if (!artist?.albums) return counts;

    counts.all = artist.albums.length;

    artist.albums.forEach((album) => {
      const albumType = (album as AlbumSummary & { album_type?: string }).album_type;
      if (albumType && albumType in counts) {
        counts[albumType as AlbumTypeFilter]++;
      } else {
        counts.album++;
      }
    });

    return counts;
  }, [artist?.albums]);

  // Filter albums based on selected type
  const filteredAlbums = useMemo(() => {
    if (!artist?.albums) return [];
    if (albumTypeFilter === "all") return artist.albums;

    return artist.albums.filter((album) => {
      const albumType = (album as AlbumSummary & { album_type?: string }).album_type;
      return albumType === albumTypeFilter || (!albumType && albumTypeFilter === "album");
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
      <div className="flex flex-col items-center justify-center py-32 gap-6">
        <div className="relative">
          <div className="w-16 h-16 rounded-full border-2 border-zinc-800 border-t-emerald-500 animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Spinner size="sm" />
          </div>
        </div>
        <p className="text-zinc-500 animate-pulse">Loading artist...</p>
      </div>
    );
  }

  if (error) {
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
            <p className="text-sm text-zinc-500 mt-2">
              {error instanceof Error ? error.message : "An error occurred"}
            </p>
            <Link to="/" className="inline-block mt-6">
              <Button variant="outline">Back to home</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!artist) {
    return (
      <div className="max-w-md mx-auto py-20">
        <Card variant="bordered">
          <CardContent className="py-10 text-center">
            <div className="w-12 h-12 rounded-full bg-zinc-800 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <p className="text-zinc-400">Artist not found</p>
            <Link to="/" className="inline-block mt-6">
              <Button variant="outline">Back to home</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Extract enhanced artist properties
  const enhancedArtist = artist as typeof artist & {
    bio?: string | null;
    origin_country?: string | null;
    origin_city?: string | null;
    formed_year?: number | null;
    related_artists?: ArtistSummary[];
    popularity?: number | null;
  };

  // Handle report submission
  const handleReportSubmit = async (report: CreateMetadataReportRequest) => {
    await createReportMutation.mutateAsync(report);
  };

  // Build report fields based on artist data
  const reportFields = [
    { name: "name", label: "Artist Name", currentValue: artist.name },
    ...(artist.genres.length > 0 ? [{ name: "genres", label: "Genres", currentValue: artist.genres.join(", ") }] : []),
    ...(enhancedArtist.bio ? [{ name: "bio", label: "Biography", currentValue: enhancedArtist.bio }] : []),
    ...(enhancedArtist.origin_country ? [{ name: "origin_country", label: "Country", currentValue: enhancedArtist.origin_country }] : []),
    ...(enhancedArtist.origin_city ? [{ name: "origin_city", label: "City", currentValue: enhancedArtist.origin_city }] : []),
    ...(enhancedArtist.formed_year ? [{ name: "formed_year", label: "Formed Year", currentValue: String(enhancedArtist.formed_year) }] : []),
  ];

  const platformLinks = artist.platforms;

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative -mx-6 -mt-6 lg:-mx-8 lg:-mt-8 overflow-hidden">
        {/* Background with gradient mesh */}
        <div className="absolute inset-0">
          {artist.image_url && (
            <>
              <img
                src={artist.image_url}
                alt=""
                className="w-full h-full object-cover blur-3xl opacity-40 scale-150"
              />
              <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0c0c0e]/80 to-[#0c0c0e]" />
            </>
          )}
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-950/20 via-transparent to-purple-950/10" />
        </div>

        {/* Content */}
        <div className="relative px-6 pt-16 pb-12 lg:px-8 lg:pt-24 lg:pb-16">
          <div className="max-w-4xl mx-auto">
            <div className="flex flex-col lg:flex-row items-center lg:items-end gap-8 animate-slide-up">
              {/* Artist Avatar */}
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-br from-emerald-500 via-emerald-400 to-teal-500 rounded-full opacity-50 blur-xl group-hover:opacity-70 transition-opacity" />
                <CoverArt
                  src={artist.image_url}
                  alt={artist.name}
                  size="hero"
                  shape="circle"
                  fallbackIcon="artist"
                  className="relative ring-4 ring-zinc-900/80 shadow-2xl"
                />
              </div>

              {/* Info */}
              <div className="flex-1 text-center lg:text-left space-y-4">
                <div>
                  <Badge variant="muted" className="mb-3 bg-zinc-800/80 backdrop-blur-sm">
                    Artist
                  </Badge>
                  <h1 className="text-4xl lg:text-6xl font-black tracking-tight text-white">
                    {artist.name}
                  </h1>
                </div>

                {/* Origin Info */}
                <OriginInfo
                  country={enhancedArtist.origin_country ?? null}
                  city={enhancedArtist.origin_city ?? null}
                  formedYear={enhancedArtist.formed_year ?? null}
                />

                {/* Genres */}
                {artist.genres.length > 0 && (
                  <div className="flex flex-wrap justify-center lg:justify-start gap-2">
                    {artist.genres.map((genre) => (
                      <span
                        key={genre}
                        className="px-3 py-1.5 text-sm text-zinc-300 bg-zinc-800/60 backdrop-blur-sm rounded-full border border-zinc-700/50 hover:border-zinc-600/50 transition-colors"
                      >
                        {genre}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Stats Grid */}
            <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 gap-3 animate-slide-up" style={{ animationDelay: "0.1s", opacity: 0 }}>
              {artist.monthly_listeners && (
                <StatCard
                  value={formatNumber(artist.monthly_listeners)}
                  label="Monthly Listeners"
                  highlight
                />
              )}
              {enhancedArtist.popularity != null && enhancedArtist.popularity > 0 && (
                <StatCard value={enhancedArtist.popularity} label="Popularity" />
              )}
              <StatCard value={artist.total_songs} label="Songs" />
              <StatCard value={artist.total_albums} label="Albums" />
            </div>

            {/* Actions */}
            <div className="mt-8 flex flex-wrap justify-center lg:justify-start gap-3 animate-slide-up" style={{ animationDelay: "0.15s", opacity: 0 }}>
              {features.canDownload && artist.songs.length > 0 && (
                <Button variant="primary" size="lg" onClick={handleDownloadAll} className="shadow-lg shadow-emerald-500/20">
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download All
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
                  variant="outline"
                  size="lg"
                  onClick={() => setShowReportModal(true)}
                  className="border-zinc-700 hover:border-zinc-600"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
      <div className="max-w-6xl mx-auto py-10 space-y-12">
        {/* Platform Links */}
        <section className="animate-slide-up" style={{ animationDelay: "0.2s", opacity: 0 }}>
          <h2 className="text-xl font-bold text-zinc-100 mb-5 tracking-tight">Listen On</h2>
          <PlatformLinksGrid platforms={platformLinks} showFollowers />
        </section>

        {/* Bio */}
        {enhancedArtist.bio && (
          <section className="animate-slide-up" style={{ animationDelay: "0.25s", opacity: 0 }}>
            <h2 className="text-xl font-bold text-zinc-100 mb-5 tracking-tight">About</h2>
            <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800/50">
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
          <section className="animate-slide-up" style={{ animationDelay: "0.35s", opacity: 0 }}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-zinc-100 tracking-tight">Discography</h2>
              <span className="text-sm text-zinc-500">{artist.albums.length} releases</span>
            </div>

            <DiscographyTabs
              activeFilter={albumTypeFilter}
              onFilterChange={setAlbumTypeFilter}
              albumCounts={albumCounts}
            />

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {filteredAlbums.map((album, index) => (
                <AlbumCard
                  key={album.id}
                  album={album as AlbumSummary & { album_type?: string }}
                  index={index}
                />
              ))}
            </div>

            {filteredAlbums.length === 0 && (
              <div className="text-center py-16 text-zinc-500">
                <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z" />
                </svg>
                No {ALBUM_TYPE_LABELS[albumTypeFilter].toLowerCase()} found
              </div>
            )}
          </section>
        )}

        {/* All Tracks */}
        {artist.songs.length > 0 && (
          <section className="animate-slide-up" style={{ animationDelay: "0.4s", opacity: 0 }}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-zinc-100 tracking-tight">All Tracks</h2>
              <span className="text-sm text-zinc-500">{artist.songs.length} songs</span>
            </div>

            <div className="rounded-2xl bg-zinc-900/30 border border-zinc-800/50 overflow-hidden">
              {/* Header */}
              <div className="flex items-center gap-4 px-4 py-3 border-b border-zinc-800/50 text-xs text-zinc-500 uppercase tracking-wider font-medium">
                <span className="w-8 text-center">#</span>
                <span className="w-12" />
                <span className="flex-1">Title</span>
                <span className="w-16 text-right">Duration</span>
                {features.canDownload && <span className="w-10" />}
              </div>

              {/* Tracks */}
              <div className="divide-y divide-zinc-800/30">
                {artist.songs.map((song, index) => (
                  <TrackRow
                    key={song.id}
                    song={song}
                    index={index}
                    onDownload={() => handleDownloadTrack(song)}
                    canDownload={features.canDownload}
                    isDownloading={findMatchesMutation.isPending}
                  />
                ))}
              </div>
            </div>
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
