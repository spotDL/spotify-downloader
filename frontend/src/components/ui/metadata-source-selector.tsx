import { clsx } from "clsx";

export interface MetadataSnapshot {
  id: string;
  source: string;
  snapshot_data: Record<string, unknown>;
  fetched_at: string;
  confidence: number;
}

export interface MetadataSourceSelectorProps {
  sources: string[];
  activeSource: string;
  onSourceChange: (source: string) => void;
  snapshots?: MetadataSnapshot[];
  className?: string;
}

const SOURCE_LABELS: Record<string, string> = {
  spotify: "Spotify",
  musicbrainz: "MusicBrainz",
  discogs: "Discogs",
  youtube_music: "YouTube Music",
  youtube: "YouTube",
  soundcloud: "SoundCloud",
  bandcamp: "Bandcamp",
  deezer: "Deezer",
  apple_music: "Apple Music",
  tidal: "Tidal",
};

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  spotify: {
    bg: "bg-[#1db954]/10",
    text: "text-[#1db954]",
    border: "border-[#1db954]/30",
  },
  musicbrainz: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/30",
  },
  discogs: {
    bg: "bg-zinc-500/10",
    text: "text-zinc-400",
    border: "border-zinc-500/30",
  },
  youtube_music: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
  },
  youtube: {
    bg: "bg-red-600/10",
    text: "text-red-500",
    border: "border-red-600/30",
  },
  soundcloud: {
    bg: "bg-orange-600/10",
    text: "text-orange-500",
    border: "border-orange-600/30",
  },
  bandcamp: {
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/30",
  },
  deezer: {
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/30",
  },
  apple_music: {
    bg: "bg-pink-500/10",
    text: "text-pink-400",
    border: "border-pink-500/30",
  },
  tidal: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/30",
  },
};

function getSourceLabel(source: string): string {
  return SOURCE_LABELS[source] || source.charAt(0).toUpperCase() + source.slice(1).replace(/_/g, " ");
}

function getSourceColors(source: string) {
  return SOURCE_COLORS[source] || {
    bg: "bg-zinc-600/10",
    text: "text-zinc-400",
    border: "border-zinc-600/30",
  };
}

/**
 * Tab-style selector for switching between metadata sources on entity pages.
 * Only displays when multiple sources are available.
 */
export function MetadataSourceSelector({
  sources,
  activeSource,
  onSourceChange,
  snapshots,
  className,
}: MetadataSourceSelectorProps) {
  // Don't render if only one source
  if (sources.length <= 1) {
    return null;
  }

  // Create a map of source to confidence
  const confidenceMap = new Map<string, number>();
  if (snapshots) {
    for (const snapshot of snapshots) {
      confidenceMap.set(snapshot.source, snapshot.confidence);
    }
  }

  return (
    <div className={clsx("flex flex-col gap-2", className)}>
      <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
        Metadata Source
      </label>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((source) => {
          const isActive = source === activeSource;
          const colors = getSourceColors(source);
          const confidence = confidenceMap.get(source);

          return (
            <button
              key={source}
              onClick={() => onSourceChange(source)}
              className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg",
                "text-sm font-medium",
                "transition-all duration-150",
                "border",
                isActive
                  ? [colors.bg, colors.text, colors.border]
                  : [
                      "bg-transparent",
                      "text-[var(--color-text-muted)]",
                      "border-transparent",
                      "hover:bg-[var(--bg-hover)]",
                      "hover:text-[var(--color-text-secondary)]",
                    ]
              )}
            >
              <SourceIcon source={source} className="w-4 h-4" />
              <span>{getSourceLabel(source)}</span>
              {confidence !== undefined && (
                <span
                  className={clsx(
                    "text-[10px] px-1.5 py-0.5 rounded",
                    isActive ? "bg-white/10" : "bg-zinc-700/50"
                  )}
                >
                  {Math.round(confidence * 100)}%
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface SourceIconProps {
  source: string;
  className?: string;
}

function SourceIcon({ source, className }: SourceIconProps) {
  const iconMap: Record<string, React.ReactNode> = {
    spotify: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
      </svg>
    ),
    musicbrainz: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <circle cx="12" cy="12" r="10" />
      </svg>
    ),
    discogs: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zm0 22.5C6.201 22.5 1.5 17.799 1.5 12S6.201 1.5 12 1.5 22.5 6.201 22.5 12 17.799 22.5 12 22.5zm0-18c-3.59 0-6.5 2.91-6.5 6.5s2.91 6.5 6.5 6.5 6.5-2.91 6.5-6.5-2.91-6.5-6.5-6.5zm0 11.5c-2.761 0-5-2.239-5-5s2.239-5 5-5 5 2.239 5 5-2.239 5-5 5z" />
      </svg>
    ),
    youtube_music: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z" />
      </svg>
    ),
    youtube: (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
  };

  return iconMap[source] || (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

export default MetadataSourceSelector;
