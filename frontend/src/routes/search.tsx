import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useUniversalSearchMutation } from "@/api/entities";
import {
  Button,
  Card,
  CardContent,
  Badge,
  Spinner,
} from "@/components/ui";
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

// Platform colors for badges
const PLATFORM_COLORS: Record<string, string> = {
  spotify: "bg-[#1db954]/20 text-[#1db954] border-[#1db954]/30",
  youtube_music: "bg-red-500/20 text-red-400 border-red-500/30",
  deezer: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  soundcloud: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  apple_music: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  tidal: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  bandcamp: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
};

// Entity type icons
function EntityIcon({ type }: { type: EntityType }) {
  switch (type) {
    case "artist":
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      );
    case "album":
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      );
    case "playlist":
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      );
    case "track":
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
        </svg>
      );
    default:
      return null;
  }
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function SearchResultCard({
  result,
  onAddToQueue,
}: {
  result: SearchResult;
  onAddToQueue?: (result: SearchResult) => void;
}) {
  const navigate = useNavigate();

  const handleClick = () => {
    // Navigate to entity page based on type
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

  return (
    <Card
      variant="bordered"
      className="cursor-pointer hover:border-emerald-700/50 transition-all duration-200 group"
      onClick={handleClick}
    >
      <CardContent className="flex items-center gap-4 py-4">
        {/* Image */}
        <div className="w-14 h-14 rounded-lg bg-zinc-800/50 overflow-hidden shrink-0 relative">
          {result.image_url ? (
            <img
              src={result.image_url}
              alt={result.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-600">
              <EntityIcon type={result.entity_type} />
            </div>
          )}
          {/* Entity type badge */}
          <div className="absolute bottom-0 right-0 bg-zinc-900/90 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 capitalize rounded-tl">
            {result.entity_type}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-zinc-100 truncate group-hover:text-emerald-400 transition-colors">
            {result.name}
          </h3>
          {result.subtitle && (
            <p className="text-sm text-zinc-500 truncate">{result.subtitle}</p>
          )}
          {/* Platform badges */}
          {result.platforms.length > 0 && (
            <div className="flex items-center gap-1.5 mt-2">
              {result.platforms.map((platform) => (
                <span
                  key={platform.platform}
                  className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${PLATFORM_COLORS[platform.platform] || "bg-zinc-800 text-zinc-400 border-zinc-700"}`}
                >
                  {platform.platform.replace("_", " ")}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Duration (for tracks) */}
        {result.duration && (
          <span className="text-sm text-zinc-500 tabular-nums">
            {formatDuration(result.duration)}
          </span>
        )}

        {/* Add to queue button (for tracks) */}
        {result.entity_type === "track" && onAddToQueue && features.canDownload && (
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onAddToQueue(result);
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Queue
          </Button>
        )}

        {/* Arrow */}
        <svg
          className="w-5 h-5 text-zinc-600 group-hover:text-emerald-400 transition-colors"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </CardContent>
    </Card>
  );
}

function SearchPage() {
  const navigate = useNavigate();
  const { q, type } = Route.useSearch();
  const [searchInput, setSearchInput] = useState(q || "");
  const [activeFilter, setActiveFilter] = useState<EntityType | "all">(type || "all");

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

    // Update URL
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
    // Navigate to queue - full implementation would find matches first
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
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-zinc-500">
        <Link to="/" className="hover:text-zinc-300">
          Home
        </Link>
        <span className="mx-2">/</span>
        <span className="text-zinc-300">Search</span>
      </nav>

      {/* Search Header */}
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-zinc-100">Search</h1>

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
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search for artists, albums, songs, or paste a URL..."
              className="w-full pl-12 pr-4 py-3 bg-zinc-900/50 border border-zinc-800 rounded-xl text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-700/50 focus:ring-1 focus:ring-emerald-700/50 transition-colors"
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
        <Card variant="bordered" className="border-red-900/50">
          <CardContent className="py-6 text-center">
            <p className="text-red-400">Search failed</p>
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
          <div className="flex items-center justify-between">
            <p className="text-sm text-zinc-400">
              Found {results.length} results
              {searchMutation.data?.entities_created
                ? ` (${searchMutation.data.entities_created} new)`
                : ""}
            </p>
            <p className="text-sm text-zinc-500">
              Query type: {searchMutation.data?.query_type || "text"}
            </p>
          </div>

          {/* Artists */}
          {(activeFilter === "all" || activeFilter === "artist") && artists.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                <EntityIcon type="artist" />
                Artists
                <Badge variant="muted" className="ml-2">{artists.length}</Badge>
              </h2>
              <div className="grid gap-3">
                {artists.slice(0, 5).map((result) => (
                  <SearchResultCard key={result.id} result={result} />
                ))}
              </div>
            </div>
          )}

          {/* Albums */}
          {(activeFilter === "all" || activeFilter === "album") && albums.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                <EntityIcon type="album" />
                Albums
                <Badge variant="muted" className="ml-2">{albums.length}</Badge>
              </h2>
              <div className="grid gap-3">
                {albums.slice(0, 5).map((result) => (
                  <SearchResultCard key={result.id} result={result} />
                ))}
              </div>
            </div>
          )}

          {/* Tracks */}
          {(activeFilter === "all" || activeFilter === "track") && tracks.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                <EntityIcon type="track" />
                Songs
                <Badge variant="muted" className="ml-2">{tracks.length}</Badge>
              </h2>
              <div className="grid gap-3">
                {tracks.map((result) => (
                  <SearchResultCard
                    key={result.id}
                    result={result}
                    onAddToQueue={handleAddToQueue}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Playlists */}
          {(activeFilter === "all" || activeFilter === "playlist") && playlists.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                <EntityIcon type="playlist" />
                Playlists
                <Badge variant="muted" className="ml-2">{playlists.length}</Badge>
              </h2>
              <div className="grid gap-3">
                {playlists.slice(0, 5).map((result) => (
                  <SearchResultCard key={result.id} result={result} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* No Results */}
      {!isLoading && !error && q && results.length === 0 && (
        <Card variant="bordered">
          <CardContent className="py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800/50 flex items-center justify-center">
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
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800/50 flex items-center justify-center">
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
