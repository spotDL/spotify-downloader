import { Link, useNavigate } from "@tanstack/react-router";
import {
  Badge,
  Button,
  RefreshMetadataButton,
} from "@/components/ui";
import { CoverArt } from "@/components/ui/cover-art";
import { useQueueStore } from "@/stores/queue";
import { useAuthStore } from "@/stores/auth";
import { useDevConfig } from "@/contexts/DevConfigContext";
import type { EnhancedSong } from "@/types";

/** Platforms that support downloading (via yt-dlp or provider hooks) -- shown only in self-hosted mode */
const DOWNLOADABLE_PLATFORMS = new Set(["youtube", "youtube_music", "soundcloud", "bandcamp", "piped"]);

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

// Key names for music notation
const KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

// Key family colors for visual distinction
const KEY_FAMILY_COLORS: Record<string, string> = {
  "C": "bg-red-900/30 text-red-400 border-red-800/50",
  "C#": "bg-rose-900/30 text-rose-400 border-rose-800/50",
  "D": "bg-orange-900/30 text-orange-400 border-orange-800/50",
  "D#": "bg-amber-900/30 text-amber-400 border-amber-800/50",
  "E": "bg-yellow-900/30 text-yellow-400 border-yellow-800/50",
  "F": "bg-lime-900/30 text-lime-400 border-lime-800/50",
  "F#": "bg-green-900/30 text-green-400 border-green-800/50",
  "G": "bg-emerald-900/30 text-emerald-400 border-emerald-800/50",
  "G#": "bg-teal-900/30 text-teal-400 border-teal-800/50",
  "A": "bg-cyan-900/30 text-cyan-400 border-cyan-800/50",
  "A#": "bg-sky-900/30 text-sky-400 border-sky-800/50",
  "B": "bg-blue-900/30 text-blue-400 border-blue-800/50",
};

function KeySignatureBadge({
  keyNum,
  mode,
}: {
  keyNum: number;
  mode: number | null;
}) {
  const keyName = KEY_NAMES[keyNum] || "?";
  const modeName = mode === 1 ? "Major" : mode === 0 ? "Minor" : "";
  const colorClass = KEY_FAMILY_COLORS[keyName] || "bg-zinc-800 text-zinc-300 border-zinc-700";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border font-medium text-sm ${colorClass}`}
      title={`Key: ${keyName} ${modeName}`}
    >
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
      </svg>
      {keyName} {modeName}
    </span>
  );
}

interface SongHeaderProps {
  song: EnhancedSong;
  displayMetadata: EnhancedSong | null;
  entityId: string;
  onRefresh: () => Promise<void>;
  onShowReportModal: () => void;
}

export function SongHeader({
  song,
  displayMetadata,
  entityId,
  onRefresh,
  onShowReportModal,
}: SongHeaderProps) {
  const navigate = useNavigate();
  const addItem = useQueueStore((state) => state.addItem);
  const { isAuthenticated } = useAuthStore();
  const { features } = useDevConfig();

  const platformsForGrid = song.platforms;

  const handleDownload = async () => {
    if (!features.canDownload || !song || !song.platforms[0]) {
      navigate({ to: "/queue" });
      return;
    }

    const downloadable = song.platforms.find(p => DOWNLOADABLE_PLATFORMS.has(p.platform)) || song.platforms[0];

    addItem(
      {
        platform: downloadable.platform,
        platform_id: downloadable.platform_id,
        url: downloadable.url,
        name: song.name,
        artists: song.artists || [song.artist],
        artist: song.artist,
        album_name: song.album_name || undefined,
        duration: song.duration,
        isrc: song.isrc || undefined,
        cover_url: song.cover_url || undefined,
      } as any
    );
    navigate({ to: "/queue" });
  };

  return (
    <div className="relative">
      {/* Background blur from cover */}
      {song.cover_url && (
        <div className="absolute inset-0 -z-10 overflow-hidden rounded-3xl">
          <img
            src={song.cover_url}
            alt=""
            className="w-full h-full object-cover blur-3xl opacity-20 scale-110"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-bg-chassis/50 to-bg-chassis" />
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-8 p-6 lg:p-8">
        {/* Cover Art - Large */}
        <div className="shrink-0 mx-auto lg:mx-0">
          <CoverArt
            src={song.cover_url}
            alt={song.name}
            size="hero"
            className="shadow-2xl shadow-black/50"
          />
        </div>

        {/* Song Info */}
        <div className="flex-1 space-y-6 text-center lg:text-left">
          {/* Title and Artist */}
          <div className="space-y-3">
            <div className="flex items-center justify-center lg:justify-start gap-2 flex-wrap">
              <Badge variant="muted" size="sm">Track</Badge>
              {song.explicit && (
                <Badge variant="warning" size="sm">Explicit</Badge>
              )}
              {song.track_number && song.disc_number && song.disc_number > 1 && (
                <Badge variant="muted" size="sm">
                  Disc {song.disc_number}, Track {song.track_number}
                </Badge>
              )}
              {song.track_number && (!song.disc_number || song.disc_number === 1) && (
                <Badge variant="muted" size="sm">
                  Track {song.track_number}
                </Badge>
              )}
            </div>
            <h1 className="text-4xl lg:text-5xl font-black tracking-tight text-zinc-50">
              {displayMetadata?.name || song.name}
            </h1>
            {song.artist_id ? (
              <Link
                to="/artist/$id"
                params={{ id: song.artist_id }}
                className="text-xl lg:text-2xl text-zinc-400 hover:text-accent-needle transition-colors"
              >
                {displayMetadata?.artist || song.artist}
              </Link>
            ) : (
              <p className="text-xl lg:text-2xl text-zinc-400">
                {displayMetadata?.artist || song.artist}
              </p>
            )}
          </div>

          {/* Quick Stats */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 text-sm">
            <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300 font-mono">
              {formatDuration(song.duration)}
            </span>
            {song.album_name && song.album_id ? (
              <Link
                to="/album/$id"
                params={{ id: song.album_id }}
                className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-300 hover:border-accent-needle/50 hover:text-accent-needle transition-colors"
              >
                {displayMetadata?.album_name || song.album_name}
              </Link>
            ) : song.album_name ? (
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400">
                {displayMetadata?.album_name || song.album_name}
              </span>
            ) : null}
            {displayMetadata?.release_date ? (
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400">
                {displayMetadata.release_date}
              </span>
            ) : displayMetadata?.year && (
              <span className="px-3 py-1.5 rounded-full bg-bg-panel border border-zinc-800 text-zinc-400">
                {displayMetadata.year}
              </span>
            )}
            {song.audio_features?.key !== null && song.audio_features?.key !== undefined && (
              <KeySignatureBadge
                keyNum={song.audio_features.key}
                mode={song.audio_features.mode}
              />
            )}
          </div>

          {/* Genres */}
          {displayMetadata?.genres && displayMetadata.genres.length > 0 && (
            <div className="flex flex-wrap justify-center lg:justify-start gap-2">
              {displayMetadata.genres.map((genre: string) => (
                <Badge key={genre} variant="default">
                  {genre}
                </Badge>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-2">
            {features.canDownload && platformsForGrid.length > 0 && (
              <Button
                variant="primary"
                size="lg"
                onClick={() => handleDownload()}
              >
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Best Match
              </Button>
            )}

            <RefreshMetadataButton
              entityId={entityId}
              onRefresh={onRefresh}
              size="lg"
            />

            {isAuthenticated && (
              <Button
                variant="ghost"
                size="lg"
                onClick={onShowReportModal}
              >
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Report Issue
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
