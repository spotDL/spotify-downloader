import { useState } from "react";
import { Button, Badge, PlatformBadge } from "@/components/ui";
import type { Song } from "@/types";

interface TrackListProps {
  tracks: Song[];
  onDownload?: (track: Song) => void;
  onPlayPreview?: (track: Song) => void;
  showAlbum?: boolean;
  showTrackNumber?: boolean;
}

export function TrackList({
  tracks,
  onDownload,
  onPlayPreview,
  showAlbum = true,
  showTrackNumber = true,
}: TrackListProps) {
  const [expandedTrack, setExpandedTrack] = useState<string | null>(null);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const totalDuration = tracks.reduce((sum, t) => sum + t.duration, 0);
  const formatTotalDuration = () => {
    const hours = Math.floor(totalDuration / 3600);
    const mins = Math.floor((totalDuration % 3600) / 60);
    if (hours > 0) {
      return `${hours} hr ${mins} min`;
    }
    return `${mins} min`;
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
        <div className="flex items-center gap-6 text-sm text-zinc-500">
          <span className="w-8 text-center">#</span>
          <span>Title</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-zinc-500">
          {showAlbum && <span className="hidden md:block w-40">Album</span>}
          <span className="w-12 text-right">
            <svg className="w-4 h-4 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </span>
          <span className="w-20"></span>
        </div>
      </div>

      {/* Track List */}
      <div className="space-y-1">
        {tracks.map((track, index) => {
          const trackKey = `${track.platform}-${track.platform_id}`;
          const isExpanded = expandedTrack === trackKey;

          return (
            <div
              key={trackKey}
              className="group relative"
            >
              <div
                className={`flex items-center justify-between px-4 py-3 rounded-lg transition-all duration-200 ${
                  isExpanded
                    ? "bg-zinc-800/80"
                    : "hover:bg-zinc-800/50"
                }`}
              >
                {/* Left side - Track info */}
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Track number / Play indicator */}
                  <div className="w-8 text-center shrink-0">
                    {showTrackNumber ? (
                      <span className="text-sm text-zinc-500 group-hover:hidden">
                        {track.track_number || index + 1}
                      </span>
                    ) : (
                      <span className="text-sm text-zinc-500 group-hover:hidden">
                        {index + 1}
                      </span>
                    )}
                    <button
                      onClick={() => onPlayPreview?.(track)}
                      className="hidden group-hover:block text-emerald-400 hover:text-emerald-300"
                    >
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </button>
                  </div>

                  {/* Cover art */}
                  <div className="w-10 h-10 rounded shrink-0">
                    {track.cover_url ? (
                      <img
                        src={track.cover_url}
                        alt={track.name}
                        className="w-10 h-10 rounded object-cover"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded bg-zinc-800 flex items-center justify-center">
                        <svg className="w-5 h-5 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                        </svg>
                      </div>
                    )}
                  </div>

                  {/* Track name and artist */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <a
                        href={`/song/${track.platform}/${track.platform_id}`}
                        className="font-medium text-zinc-100 truncate hover:underline"
                      >
                        {track.name}
                      </a>
                      {track.explicit && (
                        <Badge variant="default" size="sm" className="shrink-0">
                          E
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-zinc-400 truncate">
                      {track.artists.join(", ")}
                    </p>
                  </div>
                </div>

                {/* Right side - Album, duration, actions */}
                <div className="flex items-center gap-6">
                  {showAlbum && (
                    <span className="hidden md:block w-40 text-sm text-zinc-500 truncate">
                      {track.album_name}
                    </span>
                  )}

                  <span className="w-12 text-right text-sm text-zinc-400 font-mono tabular-nums">
                    {formatDuration(track.duration)}
                  </span>

                  <div className="w-20 flex justify-end">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedTrack(isExpanded ? null : trackKey)}
                      className="text-zinc-400 hover:text-white"
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </Button>
                    {onDownload && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDownload(track)}
                        className="text-zinc-400 hover:text-emerald-400"
                      >
                        <svg
                          className="w-4 h-4"
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
                      </Button>
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div className="px-16 py-4 bg-zinc-800/40 rounded-b-lg -mt-1 animate-slide-down">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {track.album_name && (
                      <div>
                        <span className="text-zinc-500 block">Album</span>
                        <span className="text-zinc-200">{track.album_name}</span>
                      </div>
                    )}
                    {track.year && (
                      <div>
                        <span className="text-zinc-500 block">Year</span>
                        <span className="text-zinc-200">{track.year}</span>
                      </div>
                    )}
                    {track.isrc && (
                      <div>
                        <span className="text-zinc-500 block">ISRC</span>
                        <span className="text-zinc-200 font-mono text-xs">{track.isrc}</span>
                      </div>
                    )}
                    {track.genres && track.genres.length > 0 && (
                      <div>
                        <span className="text-zinc-500 block">Genres</span>
                        <span className="text-zinc-200">{track.genres.join(", ")}</span>
                      </div>
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <PlatformBadge platform={track.platform as any} />
                    <a
                      href={track.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                    >
                      Open in {track.platform.replace("_", " ")}
                    </a>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-4 border-t border-zinc-800 text-sm text-zinc-500">
        <span>{tracks.length} {tracks.length === 1 ? "track" : "tracks"}</span>
        <span>{formatTotalDuration()}</span>
      </div>
    </div>
  );
}
