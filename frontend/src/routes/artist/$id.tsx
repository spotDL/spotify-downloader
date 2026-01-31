import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useInternalArtist } from "@/api/entities";
import { useFindMatchesMutation } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { Card, CardContent, Spinner, Badge, Button } from "@/components/ui";
import { features } from "@/config";
import type { InternalSong, PlatformInfo } from "@/types";

export const Route = createFileRoute("/artist/$id")({
  component: ArtistPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

// Platform colors
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
          {p.followers && (
            <span className="opacity-70">
              ({(p.followers / 1000).toFixed(0)}k)
            </span>
          )}
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

function ArtistPage() {
  const navigate = useNavigate();
  const { id } = Route.useParams();
  const { data: artist, isLoading, error } = useInternalArtist(id);
  const findMatchesMutation = useFindMatchesMutation();
  const { addItem } = useQueueStore();

  const handleDownloadTrack = async (track: InternalSong) => {
    if (!features.canDownload || !track.platforms[0]) {
      navigate({ to: "/queue" });
      return;
    }

    try {
      const matchResult = await findMatchesMutation.mutateAsync({
        sourceUrl: track.platforms[0].url,
        targetPlatforms: TARGET_PLATFORMS,
      });

      if (matchResult.matches.length > 0) {
        // Convert InternalSong to Song format for queue
        addItem(
          {
            platform: track.platforms[0].platform,
            platform_id: track.platforms[0].platform_id,
            url: track.platforms[0].url,
            name: track.name,
            artists: track.artists,
            artist: track.artist,
            album_name: track.album_name,
            duration: track.duration,
            isrc: track.isrc,
            cover_url: track.cover_url,
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
        <p className="text-zinc-400">Loading artist...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-red-400">Failed to load artist</p>
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

  if (!artist) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Artist not found</p>
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
        <span className="text-zinc-300">{artist.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-start gap-6">
        {/* Artist image */}
        <div className="w-40 h-40 rounded-2xl bg-zinc-800/50 overflow-hidden shrink-0">
          {artist.image_url ? (
            <img
              src={artist.image_url}
              alt={artist.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-600">
              <svg className="w-16 h-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          )}
        </div>

        {/* Artist info */}
        <div className="flex-1 space-y-4">
          <div>
            <Badge variant="muted" className="mb-2">Artist</Badge>
            <h1 className="text-3xl font-bold text-zinc-100">{artist.name}</h1>
          </div>

          {/* Genres */}
          {artist.genres.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {artist.genres.map((genre) => (
                <Badge key={genre} variant="default">
                  {genre}
                </Badge>
              ))}
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center gap-6 text-sm text-zinc-400">
            <span>{artist.total_songs} songs</span>
            <span>{artist.total_albums} albums</span>
          </div>

          {/* Platform links */}
          <PlatformBadges platforms={artist.platforms} />
        </div>
      </div>

      {/* Albums */}
      {artist.albums.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-zinc-100">Albums</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {artist.albums.map((album) => (
              <Link
                key={album.id}
                to="/album/$id"
                params={{ id: album.id }}
                className="group"
              >
                <Card variant="bordered" className="overflow-hidden hover:border-emerald-700/50 transition-colors">
                  <div className="aspect-square bg-zinc-800/50">
                    {album.cover_url ? (
                      <img
                        src={album.cover_url}
                        alt={album.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-zinc-600">
                        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <CardContent className="py-3">
                    <p className="font-medium text-sm text-zinc-100 truncate group-hover:text-emerald-400 transition-colors">
                      {album.name}
                    </p>
                    {album.year && (
                      <p className="text-xs text-zinc-500">{album.year}</p>
                    )}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Songs */}
      {artist.songs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-zinc-100">Songs</h2>
          <Card variant="bordered">
            <div className="divide-y divide-zinc-800/50">
              {artist.songs.map((song, index) => (
                <div
                  key={song.id}
                  className="flex items-center gap-4 px-4 py-3 hover:bg-zinc-800/30 transition-colors group"
                >
                  {/* Track number */}
                  <span className="w-8 text-center text-sm text-zinc-500 tabular-nums">
                    {index + 1}
                  </span>

                  {/* Cover */}
                  <div className="w-10 h-10 rounded bg-zinc-800/50 overflow-hidden shrink-0">
                    {song.cover_url ? (
                      <img
                        src={song.cover_url}
                        alt={song.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-zinc-700">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                        </svg>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-zinc-100 truncate">{song.name}</p>
                    {song.album_name && (
                      <p className="text-sm text-zinc-500 truncate">{song.album_name}</p>
                    )}
                  </div>

                  {/* Duration */}
                  <span className="text-sm text-zinc-500 tabular-nums">
                    {formatDuration(song.duration)}
                  </span>

                  {/* Download button */}
                  {features.canDownload && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDownloadTrack(song)}
                      isLoading={findMatchesMutation.isPending}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
