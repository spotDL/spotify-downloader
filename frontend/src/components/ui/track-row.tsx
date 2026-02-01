import { Link } from "@tanstack/react-router";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { CoverArt } from "@/components/ui/cover-art";
import { Button } from "@/components/ui/button";
import type { InternalSong } from "@/types";

export interface TrackRowProps {
  track: InternalSong;
  position?: number;
  showCover?: boolean;
  showAlbum?: boolean;
  showArtist?: boolean;
  showDuration?: boolean;
  isActive?: boolean;
  isPlaying?: boolean;
  onClick?: () => void;
  onDownload?: () => void;
  compact?: boolean;
  className?: string;
}

// Play indicator bars animation
const PlayingIndicator = () => (
  <div className="flex items-end justify-center gap-0.5 h-4 w-4">
    <span
      className="w-0.5 bg-[var(--accent-safe)] rounded-full animate-[equalizerSmooth_0.8s_ease-in-out_infinite]"
      style={{ height: "60%", animationDelay: "0s" }}
    />
    <span
      className="w-0.5 bg-[var(--accent-safe)] rounded-full animate-[equalizerSmooth_0.8s_ease-in-out_infinite]"
      style={{ height: "100%", animationDelay: "0.2s" }}
    />
    <span
      className="w-0.5 bg-[var(--accent-safe)] rounded-full animate-[equalizerSmooth_0.8s_ease-in-out_infinite]"
      style={{ height: "40%", animationDelay: "0.4s" }}
    />
  </div>
);

// Download icon
const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
    />
  </svg>
);

// Format seconds to mm:ss
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function TrackRow({
  track,
  position,
  showCover = true,
  showAlbum = false,
  showArtist = true,
  showDuration = true,
  isActive = false,
  isPlaying = false,
  onClick,
  onDownload,
  compact = false,
  className,
}: TrackRowProps) {
  const handleDownloadClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDownload) {
      onDownload();
    }
  };

  const content = (
    <div
      className={twMerge(
        clsx(
          "group flex items-center gap-3 transition-colors",
          compact ? "px-3 py-2" : "px-4 py-3",
          isActive
            ? "bg-[var(--accent-safe)]/10"
            : "hover:bg-[var(--bg-hover)]",
          className
        )
      )}
      onClick={onClick}
    >
      {/* Position Number or Playing Indicator */}
      {position !== undefined && (
        <div className="w-8 flex-shrink-0 text-center">
          {isPlaying ? (
            <PlayingIndicator />
          ) : (
            <span
              className={clsx(
                "text-sm font-mono",
                isActive
                  ? "text-[var(--accent-safe)]"
                  : "text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]"
              )}
            >
              {String(position).padStart(2, "0")}
            </span>
          )}
        </div>
      )}

      {/* Cover Art */}
      {showCover && (
        <CoverArt
          src={track.cover_url}
          alt={track.name}
          size="xs"
          fallbackIcon="track"
          className="flex-shrink-0"
        />
      )}

      {/* Track Info */}
      <div className="flex-1 min-w-0 space-y-0.5">
        {/* Track Name */}
        <p
          className={clsx(
            "font-medium truncate transition-colors",
            compact ? "text-sm" : "text-base",
            isActive
              ? "text-[var(--accent-safe)]"
              : "text-[var(--color-text-primary)] group-hover:text-[var(--accent-needle)]"
          )}
          title={track.name}
        >
          {track.name}
        </p>

        {/* Secondary info: Artist and/or Album */}
        {(showArtist || showAlbum) && (
          <p
            className={clsx(
              "truncate",
              compact ? "text-xs" : "text-sm",
              "text-[var(--color-text-muted)]"
            )}
          >
            {showArtist && track.artist}
            {showArtist && showAlbum && track.album_name && (
              <span className="text-[var(--color-text-dim)]"> - </span>
            )}
            {showAlbum && track.album_name && (
              <span className="text-[var(--color-text-dim)]">
                {track.album_name}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Duration */}
      {showDuration && (
        <span
          className={clsx(
            "font-mono text-[var(--color-text-muted)] flex-shrink-0",
            compact ? "text-xs" : "text-sm"
          )}
        >
          {formatDuration(track.duration)}
        </span>
      )}

      {/* Download Button */}
      {onDownload && (
        <Button
          size="sm"
          variant="ghost"
          onClick={handleDownloadClick}
          className={clsx(
            "flex-shrink-0 ml-2",
            "opacity-0 group-hover:opacity-100",
            "transition-opacity duration-150"
          )}
          aria-label={`Download ${track.name}`}
        >
          <DownloadIcon />
        </Button>
      )}
    </div>
  );

  // If there's an onClick handler, don't wrap in Link (it's already interactive)
  if (onClick) {
    return (
      <div
        className="cursor-pointer"
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        }}
      >
        {content}
      </div>
    );
  }

  // Default: wrap in Link to song page
  return (
    <Link
      to="/song/$id"
      params={{ id: track.id }}
      className={clsx(
        "block",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-inset",
        "focus-visible:ring-[var(--accent-safe)]"
      )}
    >
      {content}
    </Link>
  );
}

// Variant with a divider for list usage
export interface TrackRowListProps {
  tracks: InternalSong[];
  showCover?: boolean;
  showAlbum?: boolean;
  showArtist?: boolean;
  showDuration?: boolean;
  activeTrackId?: string;
  playingTrackId?: string;
  onTrackClick?: (track: InternalSong, index: number) => void;
  onDownload?: (track: InternalSong) => void;
  compact?: boolean;
  className?: string;
}

export function TrackRowList({
  tracks,
  showCover = true,
  showAlbum = false,
  showArtist = true,
  showDuration = true,
  activeTrackId,
  playingTrackId,
  onTrackClick,
  onDownload,
  compact = false,
  className,
}: TrackRowListProps) {
  return (
    <div
      className={twMerge(
        clsx("divide-y divide-[var(--color-border-subtle)]", className)
      )}
    >
      {tracks.map((track, index) => (
        <TrackRow
          key={track.id}
          track={track}
          position={index + 1}
          showCover={showCover}
          showAlbum={showAlbum}
          showArtist={showArtist}
          showDuration={showDuration}
          isActive={track.id === activeTrackId}
          isPlaying={track.id === playingTrackId}
          onClick={onTrackClick ? () => onTrackClick(track, index) : undefined}
          onDownload={onDownload ? () => onDownload(track) : undefined}
          compact={compact}
        />
      ))}
    </div>
  );
}

export default TrackRow;
