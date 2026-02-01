import { useState, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { CoverArt } from "@/components/ui/cover-art";
import type { AlbumSummary } from "@/types";

type AlbumFilter = "all" | "album" | "single" | "ep" | "compilation";

export interface AlbumSummaryWithType extends AlbumSummary {
  album_type?: AlbumFilter;
}

export interface DiscographyGridProps {
  albums: AlbumSummaryWithType[];
  showFilters?: boolean;
  defaultFilter?: AlbumFilter;
  onAlbumClick?: (albumId: string) => void;
  className?: string;
}

const filterTabs: { value: AlbumFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "album", label: "Albums" },
  { value: "single", label: "Singles" },
  { value: "ep", label: "EPs" },
  { value: "compilation", label: "Compilations" },
];

export function DiscographyGrid({
  albums,
  showFilters = true,
  defaultFilter = "all",
  onAlbumClick,
  className,
}: DiscographyGridProps) {
  const [activeFilter, setActiveFilter] = useState<AlbumFilter>(defaultFilter);

  // Filter albums based on active filter
  const filteredAlbums = useMemo(() => {
    if (activeFilter === "all") {
      return albums;
    }
    return albums.filter((album) => album.album_type === activeFilter);
  }, [albums, activeFilter]);

  // Get counts for each filter
  const filterCounts = useMemo(() => {
    const counts: Record<AlbumFilter, number> = {
      all: albums.length,
      album: 0,
      single: 0,
      ep: 0,
      compilation: 0,
    };

    albums.forEach((album) => {
      const type = album.album_type || "album";
      if (type in counts) {
        counts[type as AlbumFilter]++;
      }
    });

    return counts;
  }, [albums]);

  // Only show filter tabs that have albums
  const visibleFilters = filterTabs.filter(
    (tab) => tab.value === "all" || filterCounts[tab.value] > 0
  );

  return (
    <div className={twMerge(clsx("space-y-6", className))}>
      {/* Filter Tabs */}
      {showFilters && visibleFilters.length > 2 && (
        <div className="flex flex-wrap gap-2">
          {visibleFilters.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveFilter(tab.value)}
              className={clsx(
                "px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200",
                "border focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-chassis)]",
                activeFilter === tab.value
                  ? "bg-[var(--accent-safe)] text-white border-[var(--accent-safe)] shadow-lg shadow-[var(--accent-safe)]/25"
                  : "bg-[var(--bg-surface)] text-[var(--color-text-secondary)] border-[var(--color-border-subtle)] hover:bg-[var(--bg-hover)] hover:text-[var(--color-text-primary)]"
              )}
            >
              {tab.label}
              <span
                className={clsx(
                  "ml-2 text-xs",
                  activeFilter === tab.value
                    ? "text-white/80"
                    : "text-[var(--color-text-muted)]"
                )}
              >
                {filterCounts[tab.value]}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Albums Grid */}
      {filteredAlbums.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {filteredAlbums.map((album, index) => (
            <AlbumCard
              key={album.id}
              album={album}
              index={index}
              onAlbumClick={onAlbumClick}
            />
          ))}
        </div>
      ) : (
        <EmptyState filter={activeFilter} />
      )}
    </div>
  );
}

interface AlbumCardProps {
  album: AlbumSummaryWithType;
  index: number;
  onAlbumClick?: (albumId: string) => void;
}

function AlbumCard({ album, index, onAlbumClick }: AlbumCardProps) {
  const handleClick = () => {
    if (onAlbumClick) {
      onAlbumClick(album.id);
    }
  };

  const content = (
    <div
      className="group space-y-3 animate-slide-up"
      style={{ animationDelay: `${Math.min(index * 0.03, 0.3)}s` }}
    >
      {/* Album Cover */}
      <div className="relative overflow-hidden rounded-xl">
        <CoverArt
          src={album.cover_url}
          alt={album.name}
          size="lg"
          fallbackIcon="album"
          className="w-full aspect-square group-hover:scale-[1.03] transition-transform duration-300"
        />

        {/* Year Badge Overlay */}
        {album.year && (
          <div
            className={clsx(
              "absolute top-2 right-2",
              "px-2 py-0.5 rounded-md",
              "bg-black/70 backdrop-blur-sm",
              "text-xs font-mono text-zinc-300",
              "opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            )}
          >
            {album.year}
          </div>
        )}

        {/* Hover Overlay */}
        <div
          className={clsx(
            "absolute inset-0 flex items-center justify-center",
            "bg-black/40 opacity-0 group-hover:opacity-100",
            "transition-opacity duration-200"
          )}
        >
          <div
            className={clsx(
              "w-12 h-12 rounded-full",
              "bg-[var(--accent-safe)]",
              "flex items-center justify-center",
              "shadow-lg shadow-[var(--accent-safe)]/30",
              "transform scale-75 group-hover:scale-100",
              "transition-transform duration-200"
            )}
          >
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </div>
        </div>
      </div>

      {/* Album Info */}
      <div className="space-y-1">
        <p
          className={clsx(
            "font-medium text-[var(--color-text-primary)] truncate",
            "group-hover:text-[var(--accent-needle)] transition-colors"
          )}
          title={album.name}
        >
          {album.name}
        </p>
        <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
          {album.year && <span className="font-mono">{album.year}</span>}
          {album.year && album.total_tracks > 0 && (
            <span className="text-[var(--color-text-dim)]">-</span>
          )}
          {album.total_tracks > 0 && (
            <span>{album.total_tracks} tracks</span>
          )}
        </div>
      </div>
    </div>
  );

  if (onAlbumClick) {
    return (
      <button
        onClick={handleClick}
        className="text-left w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-chassis)] rounded-xl"
      >
        {content}
      </button>
    );
  }

  return (
    <Link
      to="/album/$id"
      params={{ id: album.id }}
      className="focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-chassis)] rounded-xl"
    >
      {content}
    </Link>
  );
}

interface EmptyStateProps {
  filter: AlbumFilter;
}

function EmptyState({ filter }: EmptyStateProps) {
  const filterLabels: Record<AlbumFilter, string> = {
    all: "releases",
    album: "albums",
    single: "singles",
    ep: "EPs",
    compilation: "compilations",
  };

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div
        className={clsx(
          "w-16 h-16 rounded-full mb-4",
          "bg-[var(--bg-surface)] border border-[var(--color-border-subtle)]",
          "flex items-center justify-center"
        )}
      >
        <svg
          className="w-8 h-8 text-[var(--color-text-dim)]"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 14.5c-2.49 0-4.5-2.01-4.5-4.5S9.51 7.5 12 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm0-5.5c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z" />
        </svg>
      </div>
      <p className="text-[var(--color-text-secondary)] font-medium">
        No {filterLabels[filter]} found
      </p>
      <p className="text-sm text-[var(--color-text-muted)] mt-1">
        {filter === "all"
          ? "This artist has no releases yet"
          : `Try selecting a different filter`}
      </p>
    </div>
  );
}

export default DiscographyGrid;
