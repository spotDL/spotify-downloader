import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useInternalArtist } from "@/api/entities";
import { useFindMatchesMutation, useCreateReport } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { useAuthStore } from "@/stores/auth";
import {
  Card,
  CardContent,
  Badge,
  Button,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { Spinner } from "@/components/ui";
import { PlatformLinksGrid } from "@/components/ui/platform-link";
import { ReportModal } from "@/components/ui/report-modal";
import { features } from "@/config";
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
  const CHAR_LIMIT = 200;
  const shouldTruncate = bio.length > CHAR_LIMIT;

  const displayText = isExpanded || !shouldTruncate
    ? bio
    : bio.slice(0, CHAR_LIMIT).trim() + "...";

  return (
    <Card variant="bordered">
      <CardContent>
        <p className="text-zinc-400 leading-relaxed whitespace-pre-line">
          {displayText}
        </p>
        {shouldTruncate && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-3 text-sm text-accent-needle hover:text-accent-needle/80 transition-colors font-medium"
          >
            {isExpanded ? "Show less" : "Read more"}
          </button>
        )}
      </CardContent>
    </Card>
  );
}

// Component for related artists carousel
function RelatedArtistsCarousel({ artists }: { artists: ArtistSummary[] }) {
  if (!artists || artists.length === 0) return null;

  return (
    <section>
      <h2 className="text-lg font-semibold text-zinc-300 mb-4">Related Artists</h2>
      <div className="relative">
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent">
          {artists.map((artist) => (
            <Link
              key={artist.id}
              to="/artist/$id"
              params={{ id: artist.id }}
              className="group flex-shrink-0 w-[140px]"
            >
              <div className="space-y-3 text-center">
                <CoverArt
                  src={artist.image_url}
                  alt={artist.name}
                  size="lg"
                  shape="circle"
                  fallbackIcon="artist"
                  className="mx-auto group-hover:ring-2 ring-accent-needle/50 transition-all"
                />
                <div>
                  <p className="font-medium text-zinc-100 truncate group-hover:text-accent-needle transition-colors">
                    {artist.name}
                  </p>
                  {artist.genres.length > 0 && (
                    <p className="text-xs text-zinc-500 truncate">
                      {artist.genres.slice(0, 2).join(", ")}
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
    <div className="flex flex-wrap items-center justify-center lg:justify-start gap-2 text-sm text-zinc-400">
      {parts.length > 0 && (
        <div className="flex items-center gap-1.5">
          <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>{parts[0]}</span>
        </div>
      )}
      {formedYear && (
        <div className="flex items-center gap-1.5">
          <svg className="w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span>Active since {formedYear}</span>
        </div>
      )}
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

  // Only show tabs that have albums
  const availableFilters = filters.filter(f => f === "all" || albumCounts[f] > 0);

  if (availableFilters.length <= 2) {
    // Don't show tabs if there's only one type (plus "all")
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {availableFilters.map((filter) => (
        <button
          key={filter}
          onClick={() => onFilterChange(filter)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeFilter === filter
              ? "bg-accent-needle text-black"
              : "bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          }`}
        >
          {ALBUM_TYPE_LABELS[filter]}
          {filter !== "all" && (
            <span className="ml-1.5 text-xs opacity-70">
              ({albumCounts[filter]})
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function ArtistPage() {
  const navigate = useNavigate();
  const { id } = Route.useParams();
  const { data: artist, isLoading, error } = useInternalArtist(id);
  const findMatchesMutation = useFindMatchesMutation();
  const { addItem, addBulkItems } = useQueueStore();
  const { isAuthenticated } = useAuthStore();

  const [showReportModal, setShowReportModal] = useState(false);
  const [albumTypeFilter, setAlbumTypeFilter] = useState<AlbumTypeFilter>("all");

  // Use the create report mutation - must be before any conditional returns
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
      // Check if album has album_type property (EnhancedAlbum)
      const albumType = (album as AlbumSummary & { album_type?: string }).album_type;
      if (albumType && albumType in counts) {
        counts[albumType as AlbumTypeFilter]++;
      } else {
        // Default to album if no type specified
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
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading artist...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-accent-peak">Failed to load artist</p>
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

  if (!artist) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Artist not found</p>
          <Link to="/" className="text-accent-needle hover:underline mt-4 inline-block">
            Back to home
          </Link>
        </CardContent>
      </Card>
    );
  }

  // Extract enhanced artist properties (may not exist on base InternalArtist)
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

  // Convert platforms to PlatformLink format
  const platformLinks = artist.platforms;

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Hero Section with blurred background */}
      <div className="relative -mx-6 -mt-6 lg:-mx-8 lg:-mt-8">
        {/* Background blur from artist image */}
        {artist.image_url && (
          <div className="absolute inset-0 overflow-hidden">
            <img
              src={artist.image_url}
              alt=""
              className="w-full h-full object-cover blur-3xl opacity-30 scale-125"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-bg-chassis/30 via-bg-chassis/70 to-bg-chassis" />
          </div>
        )}

        <div className="relative px-6 py-12 lg:px-8 lg:py-16">
          <div className="flex flex-col items-center text-center space-y-6">
            {/* Circular Avatar - Large hero size */}
            <CoverArt
              src={artist.image_url}
              alt={artist.name}
              size="hero"
              shape="circle"
              fallbackIcon="artist"
              className="ring-4 ring-bg-chassis shadow-2xl"
            />

            {/* Artist Name */}
            <div className="space-y-3">
              <Badge variant="muted" size="sm">Artist</Badge>
              <h1 className="text-4xl lg:text-6xl font-black tracking-tight text-zinc-50">
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
              <div className="flex flex-wrap justify-center gap-2">
                {artist.genres.map((genre) => (
                  <Badge
                    key={genre}
                    variant="default"
                    className="bg-bg-panel/80 backdrop-blur-sm"
                  >
                    {genre}
                  </Badge>
                ))}
              </div>
            )}

            {/* Stats */}
            <div className="flex items-center gap-8 text-sm">
              {artist.monthly_listeners && (
                <div className="text-center">
                  <p className="text-2xl font-bold text-accent-needle">
                    {formatNumber(artist.monthly_listeners)}
                  </p>
                  <p className="text-zinc-500">Monthly Listeners</p>
                </div>
              )}
              {enhancedArtist.popularity != null && enhancedArtist.popularity > 0 && (
                <div className="text-center">
                  <p className="text-2xl font-bold text-zinc-200">
                    {enhancedArtist.popularity}
                  </p>
                  <p className="text-zinc-500">Popularity</p>
                </div>
              )}
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-200">
                  {artist.total_songs}
                </p>
                <p className="text-zinc-500">Songs</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-200">
                  {artist.total_albums}
                </p>
                <p className="text-zinc-500">Albums</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap justify-center gap-3 pt-2">
              {features.canDownload && artist.songs.length > 0 && (
                <Button variant="primary" size="lg" onClick={handleDownloadAll}>
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download All Songs
                </Button>
              )}

              {isAuthenticated && (
                <Button
                  variant="outline"
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

      {/* Content */}
      <div className="space-y-10">
        {/* Platform Links */}
        <section>
          <h2 className="text-lg font-semibold text-zinc-300 mb-4">Listen On</h2>
          <PlatformLinksGrid platforms={platformLinks} showFollowers />
        </section>

        {/* Bio (expandable) */}
        {enhancedArtist.bio && (
          <section>
            <h2 className="text-lg font-semibold text-zinc-300 mb-4">About</h2>
            <ExpandableBio bio={enhancedArtist.bio} />
          </section>
        )}

        {/* Related Artists */}
        {enhancedArtist.related_artists && enhancedArtist.related_artists.length > 0 && (
          <RelatedArtistsCarousel artists={enhancedArtist.related_artists} />
        )}

        {/* Discography with Filter Tabs */}
        {artist.albums.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-zinc-100">Discography</h2>
              <Badge variant="muted">{artist.albums.length} releases</Badge>
            </div>

            {/* Filter Tabs */}
            <DiscographyTabs
              activeFilter={albumTypeFilter}
              onFilterChange={setAlbumTypeFilter}
              albumCounts={albumCounts}
            />

            {/* Albums Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {filteredAlbums.map((album, index) => {
                const albumType = (album as AlbumSummary & { album_type?: string }).album_type;
                return (
                  <Link
                    key={album.id}
                    to="/album/$id"
                    params={{ id: album.id }}
                    className="group animate-slide-up"
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    <div className="space-y-3">
                      {/* Album Cover */}
                      <div className="relative">
                        <CoverArt
                          src={album.cover_url}
                          alt={album.name}
                          size="lg"
                          fallbackIcon="album"
                          className="group-hover:scale-[1.03] transition-transform duration-300"
                        />
                        {/* Year Badge */}
                        {album.year && (
                          <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-black/70 backdrop-blur-sm text-xs font-mono text-zinc-300">
                            {album.year}
                          </div>
                        )}
                        {/* Album Type Badge */}
                        {albumType && albumType !== "album" && (
                          <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-accent-needle/90 backdrop-blur-sm text-xs font-medium text-black capitalize">
                            {albumType}
                          </div>
                        )}
                      </div>
                      {/* Album Info */}
                      <div>
                        <p className="font-medium text-zinc-100 truncate group-hover:text-accent-needle transition-colors">
                          {album.name}
                        </p>
                        <p className="text-sm text-zinc-500">
                          {album.total_tracks || "?"} tracks
                        </p>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>

            {filteredAlbums.length === 0 && (
              <div className="text-center py-12 text-zinc-500">
                No {ALBUM_TYPE_LABELS[albumTypeFilter].toLowerCase()} found
              </div>
            )}
          </section>
        )}

        {/* All Tracks */}
        {artist.songs.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-zinc-100">All Tracks</h2>
              <Badge variant="muted">{artist.songs.length} songs</Badge>
            </div>
            <Card variant="bordered">
              <div className="divide-y divide-zinc-800/50">
                {artist.songs.map((song, index) => (
                  <div
                    key={song.id}
                    className="flex items-center gap-4 px-4 py-3 hover:bg-zinc-800/30 transition-colors group"
                  >
                    {/* Track number */}
                    <span className="w-8 text-center text-sm font-mono text-zinc-500">
                      {String(index + 1).padStart(2, "0")}
                    </span>

                    {/* Cover */}
                    <Link to="/song/$id" params={{ id: song.id }}>
                      <CoverArt
                        src={song.cover_url}
                        alt={song.name}
                        size="xs"
                        fallbackIcon="track"
                      />
                    </Link>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <Link
                        to="/song/$id"
                        params={{ id: song.id }}
                        className="font-medium text-zinc-100 hover:text-accent-needle transition-colors truncate block"
                      >
                        {song.name}
                      </Link>
                      {song.album_name && (
                        <p className="text-sm text-zinc-500 truncate">{song.album_name}</p>
                      )}
                    </div>

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
            </Card>
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
