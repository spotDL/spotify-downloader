import { useState } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { CoverArtSize, CoverArtShape } from "@/types";

// Icons for fallback states
const FallbackIcons = {
  artist: (
    <svg className="w-1/3 h-1/3" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
  ),
  album: (
    <svg className="w-1/3 h-1/3" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 14.5c-2.49 0-4.5-2.01-4.5-4.5S9.51 7.5 12 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm0-5.5c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z" />
    </svg>
  ),
  playlist: (
    <svg className="w-1/3 h-1/3" fill="currentColor" viewBox="0 0 24 24">
      <path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18c-.31-.11-.65-.18-1-.18-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3V8h3V6h-5z" />
    </svg>
  ),
  track: (
    <svg className="w-1/3 h-1/3" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
    </svg>
  ),
};

// Play button icon
const PlayIcon = () => (
  <svg className="w-8 h-8 ml-1" fill="currentColor" viewBox="0 0 24 24">
    <path d="M8 5v14l11-7z" />
  </svg>
);

const sizeClasses: Record<CoverArtSize, string> = {
  xs: "w-12 h-12",
  sm: "w-14 h-14",
  md: "w-20 h-20",
  lg: "w-[150px] h-[150px]",
  xl: "w-[200px] h-[200px]",
  "2xl": "w-[300px] h-[300px]",
  hero: "w-[400px] h-[400px]",
};

const shapeClasses: Record<CoverArtShape, string> = {
  rounded: "rounded-xl",
  circle: "rounded-full",
};

export interface CoverArtProps {
  src: string | null;
  alt: string;
  size?: CoverArtSize;
  shape?: CoverArtShape;
  className?: string;
  fallbackIcon?: "artist" | "album" | "playlist" | "track";
  showPlayButton?: boolean;
  onPlay?: () => void;
}

export function CoverArt({
  src,
  alt,
  size = "md",
  shape = "rounded",
  className,
  fallbackIcon = "track",
  showPlayButton = false,
  onPlay,
}: CoverArtProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const showFallback = !src || hasError;

  return (
    <div
      className={twMerge(
        clsx(
          "cover-art relative overflow-hidden bg-[var(--bg-surface)] flex-shrink-0",
          sizeClasses[size],
          shapeClasses[shape],
          "group",
          className
        )
      )}
    >
      {/* Shimmer loading state */}
      {!isLoaded && !showFallback && (
        <div className="absolute inset-0 shimmer" />
      )}

      {/* Fallback icon */}
      {showFallback && (
        <div
          className={clsx(
            "absolute inset-0 flex items-center justify-center",
            "bg-gradient-to-br from-[var(--bg-elevated)] to-[var(--bg-surface)]",
            "text-[var(--color-text-dim)]"
          )}
        >
          {FallbackIcons[fallbackIcon]}
        </div>
      )}

      {/* Actual image */}
      {src && !hasError && (
        <img
          src={src}
          alt={alt}
          className={clsx(
            "w-full h-full object-cover transition-all duration-300",
            "group-hover:scale-[1.03]",
            isLoaded ? "opacity-100" : "opacity-0"
          )}
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          loading="lazy"
        />
      )}

      {/* Play button overlay */}
      {showPlayButton && onPlay && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPlay();
          }}
          className={clsx(
            "absolute inset-0 flex items-center justify-center",
            "bg-black/40 opacity-0 group-hover:opacity-100",
            "transition-opacity duration-200",
            shapeClasses[shape]
          )}
          aria-label={`Play ${alt}`}
        >
          <div
            className={clsx(
              "w-12 h-12 rounded-full bg-[var(--accent-safe)]",
              "flex items-center justify-center",
              "shadow-lg shadow-[var(--accent-safe)]/30",
              "transform transition-transform duration-200",
              "hover:scale-110"
            )}
          >
            <PlayIcon />
          </div>
        </button>
      )}
    </div>
  );
}

export default CoverArt;
