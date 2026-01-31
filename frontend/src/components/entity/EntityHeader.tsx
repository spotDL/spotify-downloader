import { Button, Badge, PlatformBadge } from "@/components/ui";
import type { DisplayEntityType } from "@/types";

interface EntityHeaderProps {
  type: DisplayEntityType;
  name: string;
  platform: string;
  imageUrl?: string | null;
  subtitle?: string | null;
  metadata?: {
    year?: number | null;
    genres?: string[];
    totalTracks?: number;
    followers?: number | null;
    description?: string | null;
  };
  onDownloadAll?: () => void;
  isDownloading?: boolean;
}

const entityTypeLabels: Record<DisplayEntityType, string> = {
  artist: "Artist",
  album: "Album",
  playlist: "Playlist",
  track: "Track",
};

const entityTypeIcons: Record<DisplayEntityType, React.ReactNode> = {
  artist: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  ),
  album: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
  playlist: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  ),
  track: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
};

export function EntityHeader({
  type,
  name,
  platform,
  imageUrl,
  subtitle,
  metadata,
  onDownloadAll,
  isDownloading,
}: EntityHeaderProps) {
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="relative p-8 bg-gradient-to-br from-zinc-900/90 via-zinc-900/80 to-zinc-900/90 rounded-2xl border border-zinc-800/50 shadow-2xl backdrop-blur-sm overflow-hidden">
      {/* Background glow */}
      <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full blur-3xl opacity-20 bg-gradient-to-br from-emerald-500 to-teal-500" />

      <div className="relative flex flex-col md:flex-row items-start gap-8">
        {/* Cover Image */}
        <div className="relative w-48 h-48 shrink-0 group">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={name}
              className={`w-48 h-48 object-cover shadow-2xl ring-1 ring-white/10 ${
                type === "artist" ? "rounded-full" : "rounded-xl"
              }`}
            />
          ) : (
            <div
              className={`w-48 h-48 bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center shadow-2xl ${
                type === "artist" ? "rounded-full" : "rounded-xl"
              }`}
            >
              <span className="text-white/70 scale-[3]">
                {entityTypeIcons[type]}
              </span>
            </div>
          )}

          {/* Type badge */}
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
            <Badge variant="default" size="sm">
              {entityTypeIcons[type]}
              <span className="ml-1">{entityTypeLabels[type]}</span>
            </Badge>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 space-y-4">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
              {name}
            </h1>
            {subtitle && (
              <p className="text-xl text-zinc-300 mt-2">{subtitle}</p>
            )}
          </div>

          {/* Metadata Row */}
          <div className="flex items-center gap-3 flex-wrap">
            <PlatformBadge platform={platform as any} />

            {metadata?.year && (
              <Badge variant="default" size="sm">
                {metadata.year}
              </Badge>
            )}

            {metadata?.totalTracks !== undefined && (
              <Badge variant="default" size="sm">
                {metadata.totalTracks} {metadata.totalTracks === 1 ? "track" : "tracks"}
              </Badge>
            )}

            {metadata?.followers !== undefined && metadata.followers !== null && (
              <Badge variant="default" size="sm">
                {formatNumber(metadata.followers)} followers
              </Badge>
            )}
          </div>

          {/* Genres */}
          {metadata?.genres && metadata.genres.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {metadata.genres.slice(0, 5).map((genre) => (
                <span
                  key={genre}
                  className="px-3 py-1 rounded-full text-sm bg-zinc-800/50 text-zinc-300 border border-zinc-700/50"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {/* Description */}
          {metadata?.description && (
            <p className="text-zinc-400 text-sm line-clamp-2 max-w-2xl">
              {metadata.description}
            </p>
          )}

          {/* Actions */}
          {onDownloadAll && type !== "track" && (
            <div className="pt-4">
              <Button
                variant="primary"
                size="lg"
                onClick={onDownloadAll}
                isLoading={isDownloading}
                disabled={isDownloading}
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Download All
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
