import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useUniversalSearchMutation } from "@/api/entities";
import {
  Button,
  Card,
  CardContent,
  Badge,
  Input,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { Spinner } from "@/components/ui";
import { SearchFilters } from "@/components/search";
import { features } from "@/config";
import type { EntityType, SearchResult } from "@/types";

interface SearchParams {
  q?: string;
  type?: EntityType;
}

export const Route = createFileRoute("/search")({
  component: SearchPage,
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    q: (search.q as string) || "",
    type: (search.type as EntityType) || undefined,
  }),
});

// ============================================================================
// SECTION BACKGROUNDS (for visual separation)
// ============================================================================

const SECTION_STYLES: Record<EntityType | "all", { bg: string; border: string; accent: string }> = {
  artist: {
    bg: "bg-gradient-to-br from-accent-needle/5 via-transparent to-transparent",
    border: "border-accent-needle/20",
    accent: "text-accent-needle",
  },
  album: {
    bg: "bg-gradient-to-br from-accent-cool/5 via-transparent to-transparent",
    border: "border-accent-cool/20",
    accent: "text-accent-cool",
  },
  track: {
    bg: "bg-gradient-to-br from-accent-safe/5 via-transparent to-transparent",
    border: "border-accent-safe/20",
    accent: "text-accent-safe",
  },
  playlist: {
    bg: "bg-gradient-to-br from-accent-warm/5 via-transparent to-transparent",
    border: "border-accent-warm/20",
    accent: "text-accent-warm",
  },
  all: {
    bg: "",
    border: "",
    accent: "",
  },
};

// ============================================================================
// ENTITY ICONS
// ============================================================================

function EntityIcon({ type, className = "w-5 h-5" }: { type: EntityType; className?: string }) {
  switch (type) {
    case "artist":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      );
    case "album":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      );
    case "playlist":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      );
    case "track":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
        </svg>
      );
    default:
      return null;
  }
}

// ============================================================================
// HELPERS
// ============================================================================

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

// ============================================================================
// QUICK ACTION BUTTONS (hover actions)
// ============================================================================

interface QuickActionsProps {
  entityType: EntityType;
  onAddToQueue?: () => void;
  onViewDetails?: () => void;
  onDownload?: () => void;
  onPlayPreview?: () => void;
}

function QuickActions({ entityType, onAddToQueue, onViewDetails, onDownload }: QuickActionsProps) {
  if (entityType === "track" && features.canDownload) {
    return (
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-200">
        {onAddToQueue && (
          <button
            onClick={(e) => { e.stopPropagation(); onAddToQueue(); }}
            className="p-2 rounded-lg bg-accent-safe/20 text-accent-safe hover:bg-accent-safe/30 transition-colors"
            title="Add to Queue"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
        {onViewDetails && (
          <button
            onClick={(e) => { e.stopPropagation(); onViewDetails(); }}
            className="p-2 rounded-lg bg-zinc-700/50 text-zinc-300 hover:bg-zinc-700 transition-colors"
            title="View Details"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  if (entityType === "album" && features.canDownload) {
    return (
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-200">
        {onDownload && (
          <button
            onClick={(e) => { e.stopPropagation(); onDownload(); }}
            className="p-2 rounded-lg bg-accent-cool/20 text-accent-cool hover:bg-accent-cool/30 transition-colors"
            title="Download Album"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        )}
        {onViewDetails && (
          <button
            onClick={(e) => { e.stopPropagation(); onViewDetails(); }}
            className="p-2 rounded-lg bg-zinc-700/50 text-zinc-300 hover:bg-zinc-700 transition-colors"
            title="View Album"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  if (entityType === "artist" && features.canDownload) {
    return (
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-200">
        {onDownload && (
          <button
            onClick={(e) => { e.stopPropagation(); onDownload(); }}
            className="p-2 rounded-lg bg-accent-needle/20 text-accent-needle hover:bg-accent-needle/30 transition-colors"
            title="Download Top Tracks"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        )}
        {onViewDetails && (
          <button
            onClick={(e) => { e.stopPropagation(); onViewDetails(); }}
            className="p-2 rounded-lg bg-zinc-700/50 text-zinc-300 hover:bg-zinc-700 transition-colors"
            title="View Artist"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  return null;
}

// ============================================================================
// ENHANCED SEARCH RESULT CARD (larger covers, quick actions)
// ============================================================================

function SearchResultCard({
  result,
  onAddToQueue,
  size = "default",
}: {
  result: SearchResult;
  onAddToQueue?: (result: SearchResult) => void;
  size?: "default" | "large";
}) {
  const navigate = useNavigate();

  const handleClick = () => {
    switch (result.entity_type) {
      case "artist":
        navigate({ to: "/artist/$id", params: { id: result.id } });
        break;
      case "album":
        navigate({ to: "/album/$id", params: { id: result.id } });
        break;
      case "playlist":
        navigate({ to: "/playlist/$id", params: { id: result.id } });
        break;
      case "track":
        navigate({ to: "/song/$id", params: { id: result.id } });
        break;
    }
  };

  const handleViewDetails = () => handleClick();

  // Use larger cover art size for main results
  const coverSize = size === "large" ? "lg" : "md";

  return (
    <div
      onClick={handleClick}
      className={`flex items-center gap-4 ${size === "large" ? "p-4" : "p-3"} rounded-xl bg-bg-panel/50 border border-zinc-800/50 hover:border-accent-needle/30 hover:bg-bg-panel cursor-pointer transition-all group`}
    >
      {/* Image - Larger for main results */}
      <CoverArt
        src={result.image_url}
        alt={result.name}
        size={coverSize}
        shape={result.entity_type === "artist" ? "circle" : "rounded"}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className={`font-medium text-zinc-100 truncate group-hover:text-accent-needle transition-colors ${size === "large" ? "text-lg" : ""}`}>
            {result.name}
          </h3>
          <Badge variant="muted" size="sm" className="capitalize shrink-0">
            {result.entity_type}
          </Badge>
        </div>
        {result.subtitle && (
          <p className={`text-zinc-500 truncate ${size === "large" ? "text-base" : "text-sm"}`}>{result.subtitle}</p>
        )}
        {/* Platform badges */}
        {result.platforms.length > 0 && (
          <div className="flex items-center gap-1.5 mt-2">
            {result.platforms.slice(0, 4).map((platform) => (
              <Badge
                key={platform.platform}
                variant="muted"
                size="sm"
                className="text-[10px] px-1.5"
              >
                {platform.platform.replace("_", " ")}
              </Badge>
            ))}
            {result.platforms.length > 4 && (
              <span className="text-[10px] text-zinc-500">
                +{result.platforms.length - 4}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Duration (for tracks) */}
      {result.duration && (
        <span className="text-sm font-mono text-zinc-500 shrink-0">
          {formatDuration(result.duration)}
        </span>
      )}

      {/* Quick Actions on hover */}
      <QuickActions
        entityType={result.entity_type}
        onAddToQueue={result.entity_type === "track" && onAddToQueue ? () => onAddToQueue(result) : undefined}
        onViewDetails={handleViewDetails}
        onDownload={result.entity_type !== "track" && onAddToQueue ? () => onAddToQueue(result) : undefined}
      />

      {/* Arrow (only show if no quick actions visible) */}
      <svg
        className="w-5 h-5 text-zinc-600 group-hover:text-accent-needle transition-colors shrink-0 group-hover:opacity-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  );
}

// ============================================================================
// ARTIST CARD (horizontal scroll)
// ============================================================================

function ArtistCard({ result, onAddToQueue }: { result: SearchResult; onAddToQueue?: (result: SearchResult) => void }) {
  const navigate = useNavigate();

  const handleClick = () => navigate({ to: "/artist/$id", params: { id: result.id } });

  return (
    <div
      onClick={handleClick}
      className="flex flex-col items-center gap-3 p-4 rounded-xl hover:bg-bg-panel cursor-pointer transition-colors group shrink-0 relative"
    >
      <CoverArt
        src={result.image_url}
        alt={result.name}
        size="lg"
        shape="circle"
        className="group-hover:scale-105 transition-transform"
      />
      <div className="text-center">
        <p className="font-medium text-zinc-100 truncate max-w-[140px] group-hover:text-accent-needle transition-colors">
          {result.name}
        </p>
        <p className="text-xs text-zinc-500">Artist</p>
      </div>
      {/* Hover action overlay */}
      {features.canDownload && onAddToQueue && (
        <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); onAddToQueue(result); }}
            className="p-1.5 rounded-full bg-accent-needle/90 text-white hover:bg-accent-needle transition-colors shadow-lg"
            title="Download Top Tracks"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// ALBUM CARD (grid view)
// ============================================================================

function AlbumCard({ result, onAddToQueue }: { result: SearchResult; onAddToQueue?: (result: SearchResult) => void }) {
  const navigate = useNavigate();

  const handleClick = () => navigate({ to: "/album/$id", params: { id: result.id } });

  return (
    <div
      onClick={handleClick}
      className="group cursor-pointer relative"
    >
      <div className="space-y-3">
        <div className="relative">
          <CoverArt
            src={result.image_url}
            alt={result.name}
            size="lg"
            className="group-hover:scale-[1.03] transition-transform duration-300"
          />
          {/* Hover action overlay */}
          {features.canDownload && onAddToQueue && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl">
              <button
                onClick={(e) => { e.stopPropagation(); onAddToQueue(result); }}
                className="p-3 rounded-full bg-accent-cool text-white hover:bg-accent-cool/90 transition-colors shadow-lg"
                title="Download Album"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </button>
            </div>
          )}
        </div>
        <div>
          <p className="font-medium text-zinc-100 truncate group-hover:text-accent-needle transition-colors">
            {result.name}
          </p>
          <p className="text-sm text-zinc-500 truncate">{result.subtitle}</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SECTION DIVIDER
// ============================================================================

function SectionDivider({ type, count }: { type: EntityType; count: number }) {
  const styles = SECTION_STYLES[type];
  const labels: Record<EntityType, string> = {
    artist: "Artists",
    album: "Albums",
    track: "Songs",
    playlist: "Playlists",
    all: "All",
  };

  return (
    <div className={`flex items-center gap-3 p-4 rounded-xl ${styles.bg} border ${styles.border} mb-4`}>
      <div className={`p-2 rounded-lg bg-bg-panel ${styles.accent}`}>
        <EntityIcon type={type} className="w-5 h-5" />
      </div>
      <div className="flex-1">
        <h2 className="text-lg font-semibold text-zinc-100">{labels[type]}</h2>
      </div>
      <Badge variant="muted" size="sm" className="text-sm px-2.5 py-1">
        {count} {count === 1 ? "result" : "results"}
      </Badge>
    </div>
  );
}

// ============================================================================
// MAIN SEARCH PAGE
// ============================================================================

function SearchPage() {
  const navigate = useNavigate();
  const { q, type } = Route.useSearch();
  const [searchInput, setSearchInput] = useState(q || "");
  const [activeFilter, setActiveFilter] = useState<EntityType | "all">(type || "all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");

  const searchMutation = useUniversalSearchMutation();

  // Search on mount or query change
  useEffect(() => {
    if (q) {
      setSearchInput(q);
      searchMutation.mutate({
        query: q,
        entity_types: type && type !== "all" ? [type] : undefined,
        limit: 30,
      });
    }
  }, [q, type]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchInput.trim();
    if (!query) return;

    navigate({
      to: "/search",
      search: {
        q: query,
        type: activeFilter !== "all" ? activeFilter : undefined,
      },
    });
  };

  const handleFilterChange = (filter: EntityType | "all") => {
    setActiveFilter(filter);
    if (searchInput.trim()) {
      navigate({
        to: "/search",
        search: {
          q: searchInput.trim(),
          type: filter !== "all" ? filter : undefined,
        },
      });
    }
  };

  const handleAddToQueue = async (_result: SearchResult) => {
    navigate({ to: "/queue" });
  };

  const results = searchMutation.data?.results || [];
  const isLoading = searchMutation.isPending;
  const error = searchMutation.error;

  // Group results by entity type
  const artists = results.filter((r) => r.entity_type === "artist");
  const albums = results.filter((r) => r.entity_type === "album");
  const tracks = results.filter((r) => r.entity_type === "track");
  const playlists = results.filter((r) => r.entity_type === "playlist");

  return (
    <div className="space-y-8 animate-slide-up">
      {/* Search Header */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-zinc-100">Search</h1>
          {results.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode("list")}
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === "list"
                    ? "bg-accent-needle/20 text-accent-needle"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
              </button>
              <button
                onClick={() => setViewMode("grid")}
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === "grid"
                    ? "bg-accent-needle/20 text-accent-needle"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg
                className="w-5 h-5 text-zinc-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <Input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search for artists, albums, songs, or paste a URL..."
              className="pl-12"
            />
          </div>
          <Button type="submit" isLoading={isLoading} disabled={!searchInput.trim()}>
            Search
          </Button>
        </form>

        {/* Filters */}
        <SearchFilters activeFilter={activeFilter} onFilterChange={handleFilterChange} />
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <Spinner size="lg" />
          <p className="text-zinc-400">Searching across all platforms...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card variant="bordered" className="border-accent-peak/50 bg-accent-peak/5">
          <CardContent className="py-6 text-center">
            <p className="text-accent-peak">Search failed</p>
            <p className="text-sm text-zinc-500 mt-2">
              {error instanceof Error ? error.message : "An error occurred"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {!isLoading && !error && results.length > 0 && (
        <div className="space-y-8">
          {/* Results summary */}
          <div className="flex items-center justify-between px-1">
            <p className="text-sm text-zinc-400">
              Found <span className="text-zinc-200 font-medium">{results.length}</span> results
              {searchMutation.data?.entities_created
                ? ` (${searchMutation.data.entities_created} new)`
                : ""}
            </p>
            <p className="text-sm text-zinc-500">
              Query type: <span className="text-zinc-400">{searchMutation.data?.query_type || "text"}</span>
            </p>
          </div>

          {/* Artists - Horizontal scroll with section divider */}
          {(activeFilter === "all" || activeFilter === "artist") && artists.length > 0 && (
            <section className="space-y-0">
              <SectionDivider type="artist" count={artists.length} />
              <div className="flex gap-2 overflow-x-auto pb-4 -mx-2 px-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-zinc-700">
                {artists.map((result) => (
                  <ArtistCard key={result.id} result={result} onAddToQueue={handleAddToQueue} />
                ))}
              </div>
            </section>
          )}

          {/* Albums - Grid or List with section divider */}
          {(activeFilter === "all" || activeFilter === "album") && albums.length > 0 && (
            <section className="space-y-0">
              <SectionDivider type="album" count={albums.length} />
              {viewMode === "grid" ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                  {albums.map((result) => (
                    <AlbumCard key={result.id} result={result} onAddToQueue={handleAddToQueue} />
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {albums.map((result) => (
                    <SearchResultCard key={result.id} result={result} size="large" onAddToQueue={handleAddToQueue} />
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Tracks - List with section divider and larger covers */}
          {(activeFilter === "all" || activeFilter === "track") && tracks.length > 0 && (
            <section className="space-y-0">
              <SectionDivider type="track" count={tracks.length} />
              <div className="space-y-2">
                {tracks.map((result) => (
                  <SearchResultCard
                    key={result.id}
                    result={result}
                    size="large"
                    onAddToQueue={handleAddToQueue}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Playlists with section divider */}
          {(activeFilter === "all" || activeFilter === "playlist") && playlists.length > 0 && (
            <section className="space-y-0">
              <SectionDivider type="playlist" count={playlists.length} />
              <div className="space-y-2">
                {playlists.map((result) => (
                  <SearchResultCard key={result.id} result={result} size="large" onAddToQueue={handleAddToQueue} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* No Results */}
      {!isLoading && !error && q && results.length === 0 && (
        <Card variant="bordered">
          <CardContent className="py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-bg-panel flex items-center justify-center">
              <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-zinc-300">No results found</h3>
            <p className="text-zinc-500 mt-2">
              Try a different search term or paste a URL directly
            </p>
          </CardContent>
        </Card>
      )}

      {/* Empty State (no search) */}
      {!q && !isLoading && (
        <Card variant="bordered">
          <CardContent className="py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-bg-panel flex items-center justify-center">
              <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-zinc-300">Search for music</h3>
            <p className="text-zinc-500 mt-2">
              Enter an artist, album, song name, or paste a URL
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
