import { useRef, useState, useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { CoverArt } from "@/components/ui/cover-art";
import { Badge } from "@/components/ui/badge";
import type { ArtistSummary } from "@/types";

export interface RelatedArtistsCarouselProps {
  artists: ArtistSummary[];
  onArtistClick?: (artistId: string) => void;
  className?: string;
}

// Chevron Left Icon
const ChevronLeftIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
);

// Chevron Right Icon
const ChevronRightIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

export function RelatedArtistsCarousel({
  artists,
  onArtistClick,
  className,
}: RelatedArtistsCarouselProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Check scroll position
  const checkScrollPosition = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollLeft, scrollWidth, clientWidth } = container;
    setCanScrollLeft(scrollLeft > 0);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 1);
  };

  // Update scroll position on mount and resize
  useEffect(() => {
    checkScrollPosition();
    window.addEventListener("resize", checkScrollPosition);
    return () => window.removeEventListener("resize", checkScrollPosition);
  }, [artists]);

  // Scroll functions
  const scrollLeft = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const scrollAmount = container.clientWidth * 0.8;
    container.scrollBy({ left: -scrollAmount, behavior: "smooth" });
  };

  const scrollRight = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const scrollAmount = container.clientWidth * 0.8;
    container.scrollBy({ left: scrollAmount, behavior: "smooth" });
  };

  if (artists.length === 0) {
    return null;
  }

  return (
    <div className={twMerge(clsx("relative group/carousel", className))}>
      {/* Scroll Buttons (Desktop) */}
      {canScrollLeft && (
        <button
          onClick={scrollLeft}
          className={clsx(
            "absolute left-0 top-1/2 -translate-y-1/2 z-10",
            "w-10 h-10 rounded-full",
            "bg-[var(--bg-panel)]/90 backdrop-blur-sm",
            "border border-[var(--color-border)]",
            "flex items-center justify-center",
            "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
            "shadow-lg",
            "opacity-0 group-hover/carousel:opacity-100",
            "transition-all duration-200",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)]",
            "-ml-5 hidden md:flex"
          )}
          aria-label="Scroll left"
        >
          <ChevronLeftIcon />
        </button>
      )}

      {canScrollRight && (
        <button
          onClick={scrollRight}
          className={clsx(
            "absolute right-0 top-1/2 -translate-y-1/2 z-10",
            "w-10 h-10 rounded-full",
            "bg-[var(--bg-panel)]/90 backdrop-blur-sm",
            "border border-[var(--color-border)]",
            "flex items-center justify-center",
            "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
            "shadow-lg",
            "opacity-0 group-hover/carousel:opacity-100",
            "transition-all duration-200",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-safe)]",
            "-mr-5 hidden md:flex"
          )}
          aria-label="Scroll right"
        >
          <ChevronRightIcon />
        </button>
      )}

      {/* Gradient Overlays for scroll indication */}
      {canScrollLeft && (
        <div
          className={clsx(
            "absolute left-0 top-0 bottom-0 w-12 z-[5]",
            "bg-gradient-to-r from-[var(--bg-chassis)] to-transparent",
            "pointer-events-none"
          )}
        />
      )}
      {canScrollRight && (
        <div
          className={clsx(
            "absolute right-0 top-0 bottom-0 w-12 z-[5]",
            "bg-gradient-to-l from-[var(--bg-chassis)] to-transparent",
            "pointer-events-none"
          )}
        />
      )}

      {/* Scrollable Container */}
      <div
        ref={scrollContainerRef}
        onScroll={checkScrollPosition}
        className={clsx(
          "flex gap-4 overflow-x-auto",
          "scroll-smooth scrollbar-hide",
          "pb-2 -mb-2" // Prevent clipping of shadows
        )}
      >
        {artists.map((artist, index) => (
          <ArtistCard
            key={artist.id}
            artist={artist}
            index={index}
            onArtistClick={onArtistClick}
          />
        ))}
      </div>
    </div>
  );
}

interface ArtistCardProps {
  artist: ArtistSummary;
  index: number;
  onArtistClick?: (artistId: string) => void;
}

function ArtistCard({ artist, index, onArtistClick }: ArtistCardProps) {
  const handleClick = () => {
    if (onArtistClick) {
      onArtistClick(artist.id);
    }
  };

  // Get first 2 genres
  const displayGenres = artist.genres.slice(0, 2);

  const content = (
    <div
      className={clsx(
        "group flex-shrink-0 w-32 sm:w-36",
        "text-center space-y-3",
        "animate-slide-up"
      )}
      style={{ animationDelay: `${Math.min(index * 0.05, 0.3)}s` }}
    >
      {/* Circular Artist Image */}
      <div className="relative mx-auto">
        <CoverArt
          src={artist.image_url}
          alt={artist.name}
          size="lg"
          shape="circle"
          fallbackIcon="artist"
          className={clsx(
            "mx-auto",
            "ring-2 ring-transparent",
            "group-hover:ring-[var(--accent-safe)]/50",
            "transition-all duration-300",
            "group-hover:scale-105"
          )}
        />

        {/* Hover glow effect */}
        <div
          className={clsx(
            "absolute inset-0 rounded-full",
            "bg-[var(--accent-safe)]/0 group-hover:bg-[var(--accent-safe)]/10",
            "transition-colors duration-300"
          )}
        />
      </div>

      {/* Artist Name */}
      <div className="space-y-1.5 px-1">
        <p
          className={clsx(
            "font-medium text-sm text-[var(--color-text-primary)]",
            "truncate",
            "group-hover:text-[var(--accent-needle)]",
            "transition-colors duration-200"
          )}
          title={artist.name}
        >
          {artist.name}
        </p>

        {/* Genre Badges */}
        {displayGenres.length > 0 && (
          <div className="flex flex-wrap justify-center gap-1">
            {displayGenres.map((genre) => (
              <Badge
                key={genre}
                variant="muted"
                size="sm"
                className="text-[10px] px-1.5 py-0.5 truncate max-w-full"
              >
                {genre}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  if (onArtistClick) {
    return (
      <button
        onClick={handleClick}
        className={clsx(
          "text-center",
          "focus:outline-none focus-visible:ring-2",
          "focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2",
          "focus-visible:ring-offset-[var(--bg-chassis)]",
          "rounded-xl"
        )}
      >
        {content}
      </button>
    );
  }

  return (
    <Link
      to="/artist/$id"
      params={{ id: artist.id }}
      className={clsx(
        "focus:outline-none focus-visible:ring-2",
        "focus-visible:ring-[var(--accent-safe)] focus-visible:ring-offset-2",
        "focus-visible:ring-offset-[var(--bg-chassis)]",
        "rounded-xl"
      )}
    >
      {content}
    </Link>
  );
}

export default RelatedArtistsCarousel;
