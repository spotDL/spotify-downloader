import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useInternalSong } from "@/api/entities";
import { useFindMatchesMutation } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { Card, CardContent, Spinner, Badge, Button } from "@/components/ui";
import { features } from "@/config";
import type { PlatformInfo } from "@/types";

export const Route = createFileRoute("/song/$id")({
  component: SongPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

const PLATFORM_COLORS: Record<string, string> = {
  spotify: "bg-[#1db954]/20 text-[#1db954] border-[#1db954]/30",
  youtube_music: "bg-red-500/20 text-red-400 border-red-500/30",
  deezer: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  soundcloud: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  apple_music: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  tidal: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  bandcamp: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
};

function PlatformBadges({ platforms }: { platforms: PlatformInfo[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {platforms.map((p) => (
        <a
          key={p.platform}
          href={p.url}
          target="_blank"
          rel="noopener noreferrer"
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors hover:opacity-80 ${PLATFORM_COLORS[p.platform] || "bg-zinc-800 text-zinc-400 border-zinc-700"}`}
          onClick={(e) => e.stopPropagation()}
        >
          {p.platform.replace("_", " ")}
        </a>
      ))}
    </div>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function SongPage() {
  const navigate = useNavigate();
  const { id } = Route.useParams();
  const { data: song, isLoading, error } = useInternalSong(id);
  const findMatchesMutation = useFindMatchesMutation();
  const addItem = useQueueStore((state) => state.addItem);

  const handleDownload = async () => {
    if (!features.canDownload || !song || !song.platforms[0]) {
      navigate({ to: "/queue" });
      return;
    }

    try {
      const matchResult = await findMatchesMutation.mutateAsync({
        sourceUrl: song.platforms[0].url,
        targetPlatforms: TARGET_PLATFORMS,
      });

      if (matchResult.matches.length > 0) {
        addItem(
          {
            platform: song.platforms[0].platform,
            platform_id: song.platforms[0].platform_id,
            url: song.platforms[0].url,
            name: song.name,
            artists: song.artists,
            artist: song.artist,
            album_name: song.album_name,
            duration: song.duration,
            isrc: song.isrc,
            cover_url: song.cover_url,
          },
          matchResult.matches[0]
        );
        navigate({ to: "/queue" });
      }
    } catch (err) {
      console.error("Failed to find matches:", err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading song...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-red-400">Failed to load song</p>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
          <Link to="/" className="text-emerald-400 hover:underline mt-4 inline-block">
            Back to home
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (!song) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Song not found</p>
          <Link to="/" className="text-emerald-400 hover:underline mt-4 inline-block">
            Back to home
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-zinc-500">
        <Link to="/" className="hover:text-zinc-300">
          Home
        </Link>
        <span className="mx-2">/</span>
        <Link to="/search" className="hover:text-zinc-300">
          Search
        </Link>
        <span className="mx-2">/</span>
        <span className="text-zinc-300">{song.name}</span>
      </nav>

      {/* Song details */}
      <div className="flex items-start gap-6">
        {/* Cover */}
        <div className="w-48 h-48 rounded-2xl bg-zinc-800/50 overflow-hidden shrink-0 shadow-2xl">
          {song.cover_url ? (
            <img
              src={song.cover_url}
              alt={song.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-600">
              <svg className="w-20 h-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 space-y-4">
          <div>
            <Badge variant="muted" className="mb-2">Song</Badge>
            <h1 className="text-3xl font-bold text-zinc-100">{song.name}</h1>
            <p className="text-lg text-zinc-400">{song.artist}</p>
          </div>

          {/* Metadata */}
          <div className="flex items-center gap-6 text-sm text-zinc-400">
            <span>{formatDuration(song.duration)}</span>
            {song.album_name && <span>{song.album_name}</span>}
            {song.year && <span>{song.year}</span>}
            {song.isrc && (
              <span className="font-mono text-xs text-zinc-500">
                ISRC: {song.isrc}
              </span>
            )}
          </div>

          {/* Platform links */}
          <PlatformBadges platforms={song.platforms} />

          {/* Download button */}
          {features.canDownload && (
            <Button
              onClick={handleDownload}
              isLoading={findMatchesMutation.isPending}
              className="mt-4"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
