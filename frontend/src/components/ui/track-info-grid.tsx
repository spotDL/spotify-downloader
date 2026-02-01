import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { EnhancedSong } from "@/types";
import { Badge } from "./badge";
import { AudioFeaturesSummary } from "./audio-features-panel";

export interface TrackInfoGridProps {
  /** Enhanced song data */
  track: EnhancedSong;
  /** Whether to show audio features summary */
  showAudioFeatures?: boolean;
  /** Whether to show technical information (ISRC, Platform IDs) */
  showTechnical?: boolean;
  /** Additional class names */
  className?: string;
}

// Format duration in mm:ss
function formatDuration(durationMs: number): string {
  const totalSeconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

// Format release date
function formatReleaseDate(dateStr: string | null): string {
  if (!dateStr) return "--";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

// Info item component
interface InfoItemProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  className?: string;
}

function InfoItem({ label, value, mono = false, className }: InfoItemProps) {
  return (
    <div className={twMerge("flex flex-col gap-0.5", className)}>
      <span className="text-xs text-[var(--color-text-dim)] uppercase tracking-wider">
        {label}
      </span>
      <span
        className={clsx(
          "text-sm text-[var(--color-text-primary)]",
          mono && "font-mono"
        )}
      >
        {value || "--"}
      </span>
    </div>
  );
}

// Section header component
interface SectionHeaderProps {
  title: string;
  className?: string;
}

function SectionHeader({ title, className }: SectionHeaderProps) {
  return (
    <h4
      className={twMerge(
        "text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3",
        className
      )}
    >
      {title}
    </h4>
  );
}

/**
 * Reusable grid layout for track information
 */
export function TrackInfoGrid({
  track,
  showAudioFeatures = true,
  showTechnical = true,
  className,
}: TrackInfoGridProps) {
  const hasTrackPosition = track.track_number !== null || track.disc_number !== null;
  const hasGenres = track.genres && track.genres.length > 0;
  const hasLabelInfo = track.label || track.copyright_text;
  const hasPlatformIds = track.platforms && track.platforms.length > 0;

  return (
    <div
      className={twMerge(
        clsx(
          "bg-[var(--bg-panel)] border border-[var(--color-border-subtle)]",
          "rounded-2xl p-5",
          "transition-all duration-200",
          "hover:border-[var(--color-border)]"
        ),
        className
      )}
    >
      {/* Basic Info Section */}
      <section className="mb-5">
        <SectionHeader title="Track Info" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <InfoItem
            label="Duration"
            value={formatDuration(track.duration)}
            mono
          />
          <InfoItem
            label="Release Date"
            value={formatReleaseDate(track.release_date)}
          />
          {track.year && (
            <InfoItem label="Year" value={track.year} mono />
          )}
          {track.popularity !== null && (
            <InfoItem
              label="Popularity"
              value={
                <div className="flex items-center gap-2">
                  <span className="font-mono">{track.popularity}</span>
                  <div className="flex-1 h-1 bg-[var(--bg-surface)] rounded-full overflow-hidden max-w-[60px]">
                    <div
                      className="h-full bg-[var(--accent-safe)] rounded-full"
                      style={{ width: `${track.popularity}%` }}
                    />
                  </div>
                </div>
              }
            />
          )}
        </div>
      </section>

      {/* Track Position */}
      {hasTrackPosition && (
        <section className="mb-5">
          <SectionHeader title="Track Position" />
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {track.track_number !== null && (
              <InfoItem
                label="Track #"
                value={track.track_number}
                mono
              />
            )}
            {track.disc_number !== null && (
              <InfoItem
                label="Disc #"
                value={track.disc_number}
                mono
              />
            )}
            {track.album_name && (
              <InfoItem
                label="Album"
                value={track.album_name}
              />
            )}
          </div>
        </section>
      )}

      {/* Technical Info */}
      {showTechnical && (
        <section className="mb-5">
          <SectionHeader title="Technical" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {track.isrc && (
              <InfoItem
                label="ISRC"
                value={
                  <span className="font-mono text-xs bg-[var(--bg-surface)] px-2 py-1 rounded">
                    {track.isrc}
                  </span>
                }
              />
            )}
            {hasPlatformIds && (
              <InfoItem
                label="Platform IDs"
                value={
                  <div className="flex flex-wrap gap-1">
                    {track.platforms.slice(0, 3).map((p) => (
                      <span
                        key={`${p.platform}-${p.platform_id}`}
                        className="text-xs bg-[var(--bg-surface)] px-2 py-0.5 rounded font-mono"
                        title={`${p.platform}: ${p.platform_id}`}
                      >
                        {p.platform.charAt(0).toUpperCase()}: {p.platform_id.slice(0, 8)}...
                      </span>
                    ))}
                    {track.platforms.length > 3 && (
                      <span className="text-xs text-[var(--color-text-dim)]">
                        +{track.platforms.length - 3} more
                      </span>
                    )}
                  </div>
                }
              />
            )}
            <InfoItem
              label="Matches"
              value={
                <span className="font-mono text-[var(--accent-safe)]">
                  {track.matches_count}
                </span>
              }
            />
          </div>
        </section>
      )}

      {/* Label & Copyright */}
      {hasLabelInfo && (
        <section className="mb-5">
          <SectionHeader title="Label & Copyright" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {track.label && (
              <InfoItem label="Label" value={track.label} />
            )}
            {track.copyright_text && (
              <InfoItem
                label="Copyright"
                value={
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {track.copyright_text}
                  </span>
                }
              />
            )}
          </div>
        </section>
      )}

      {/* Genres */}
      {hasGenres && (
        <section className="mb-5">
          <SectionHeader title="Genres" />
          <div className="flex flex-wrap gap-2">
            {track.genres.map((genre) => (
              <Badge
                key={genre}
                variant="default"
                size="sm"
              >
                {genre}
              </Badge>
            ))}
          </div>
        </section>
      )}

      {/* Explicit & Other Flags */}
      <section className="mb-5">
        <SectionHeader title="Flags" />
        <div className="flex flex-wrap gap-2">
          {track.explicit ? (
            <Badge variant="warning" size="sm">
              Explicit
            </Badge>
          ) : (
            <Badge variant="muted" size="sm">
              Clean
            </Badge>
          )}
        </div>
      </section>

      {/* Audio Features Summary */}
      {showAudioFeatures && track.audio_features && (
        <section>
          <SectionHeader title="Audio Features" />
          <AudioFeaturesSummary features={track.audio_features} />
        </section>
      )}
    </div>
  );
}

/**
 * Compact track info row for use in lists
 */
export interface TrackInfoRowProps {
  track: EnhancedSong;
  showDuration?: boolean;
  showYear?: boolean;
  showExplicit?: boolean;
  className?: string;
}

export function TrackInfoRow({
  track,
  showDuration = true,
  showYear = true,
  showExplicit = true,
  className,
}: TrackInfoRowProps) {
  return (
    <div
      className={twMerge(
        "flex items-center gap-3 text-sm text-[var(--color-text-muted)]",
        className
      )}
    >
      {showDuration && (
        <span className="font-mono">{formatDuration(track.duration)}</span>
      )}
      {showYear && track.year && (
        <>
          <span className="text-[var(--color-text-dim)]">/</span>
          <span>{track.year}</span>
        </>
      )}
      {showExplicit && track.explicit && (
        <Badge variant="warning" size="sm">
          E
        </Badge>
      )}
      {track.isrc && (
        <>
          <span className="text-[var(--color-text-dim)]">/</span>
          <span className="font-mono text-xs">{track.isrc}</span>
        </>
      )}
    </div>
  );
}

/**
 * Mini track card for compact displays
 */
export interface MiniTrackCardProps {
  track: EnhancedSong;
  onClick?: () => void;
  className?: string;
}

export function MiniTrackCard({
  track,
  onClick,
  className,
}: MiniTrackCardProps) {
  return (
    <div
      className={twMerge(
        clsx(
          "flex items-center gap-3 p-3",
          "bg-[var(--bg-surface)] rounded-xl",
          "border border-[var(--color-border-subtle)]",
          "transition-all duration-200",
          "hover:border-[var(--color-border)]",
          onClick && "cursor-pointer hover:bg-[var(--bg-hover)]"
        ),
        className
      )}
      onClick={onClick}
    >
      {/* Cover art placeholder */}
      <div
        className={clsx(
          "w-12 h-12 rounded-lg flex-shrink-0",
          "bg-[var(--bg-panel)] flex items-center justify-center"
        )}
      >
        {track.cover_url ? (
          <img
            src={track.cover_url}
            alt={track.name}
            className="w-full h-full object-cover rounded-lg"
          />
        ) : (
          <svg
            className="w-5 h-5 text-[var(--color-text-dim)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
            />
          </svg>
        )}
      </div>

      {/* Track info */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-[var(--color-text-primary)] truncate">
          {track.name}
        </h4>
        <p className="text-xs text-[var(--color-text-muted)] truncate">
          {track.artist}
        </p>
      </div>

      {/* Duration */}
      <span className="text-xs font-mono text-[var(--color-text-dim)] flex-shrink-0">
        {formatDuration(track.duration)}
      </span>
    </div>
  );
}

export default TrackInfoGrid;
