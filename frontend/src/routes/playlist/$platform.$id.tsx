import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { usePlaylist, useFindMatchesMutation } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { EntityHeader, TrackList } from "@/components/entity";
import { Card, CardContent, Spinner } from "@/components/ui";
import { features } from "@/config";
import type { Song } from "@/types";

export const Route = createFileRoute("/playlist/$platform/$id" as const)({
  component: PlaylistPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function PlaylistPage() {
  const navigate = useNavigate();
  const { platform, id } = Route.useParams();
  const { data: playlist, isLoading, error } = usePlaylist(platform, id);
  const findMatchesMutation = useFindMatchesMutation();
  const { addItem, addBulkItems } = useQueueStore();

  const handleDownloadTrack = async (track: Song) => {
    if (!features.canDownload) {
      navigate({ to: "/queue" });
      return;
    }

    try {
      const matchResult = await findMatchesMutation.mutateAsync({
        sourceUrl: track.url,
        targetPlatforms: TARGET_PLATFORMS,
      });

      if (matchResult.matches.length > 0) {
        addItem(track, matchResult.matches[0]);
        navigate({ to: "/queue" });
      }
    } catch (err) {
      console.error("Failed to find matches:", err);
    }
  };

  const handleDownloadAll = async () => {
    if (!features.canDownload || !playlist?.songs.length) {
      navigate({ to: "/queue" });
      return;
    }

    const songsWithMatches: Array<{ song: Song; matchUrl?: string }> = [];

    for (const track of playlist.songs) {
      try {
        const matchResult = await findMatchesMutation.mutateAsync({
          sourceUrl: track.url,
          targetPlatforms: TARGET_PLATFORMS,
        });

        if (matchResult.matches.length > 0) {
          songsWithMatches.push({ song: track, matchUrl: matchResult.matches[0].target_url });
        }
      } catch (err) {
        console.error(`Failed to find match for ${track.name}:`, err);
      }
    }

    if (songsWithMatches.length > 0 && addBulkItems) {
      addBulkItems(
        songsWithMatches.map((s) => s.song),
        {
          type: "playlist",
          name: playlist.name,
          url: playlist.url,
        }
      );
      navigate({ to: "/queue" });
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading playlist...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-red-400">Failed to load playlist</p>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
          <Link to="/" className="text-emerald-400 hover:underline mt-4 inline-block">
            Back to search
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (!playlist) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Playlist not found</p>
          <Link to="/" className="text-emerald-400 hover:underline mt-4 inline-block">
            Back to search
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
        <span className="text-zinc-300">{playlist.name}</span>
      </nav>

      {/* Header */}
      <EntityHeader
        type="playlist"
        name={playlist.name}
        platform={playlist.platform}
        imageUrl={playlist.cover_url}
        subtitle={playlist.owner_name}
        metadata={{
          totalTracks: playlist.total_tracks,
          description: playlist.description,
        }}
        onDownloadAll={features.canDownload ? handleDownloadAll : undefined}
        isDownloading={findMatchesMutation.isPending}
      />

      {/* Tracks */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-100">Tracks</h2>
        <Card variant="bordered">
          <TrackList
            tracks={playlist.songs}
            onDownload={features.canDownload ? handleDownloadTrack : undefined}
            showAlbum={true}
            showTrackNumber={false}
          />
        </Card>
      </div>
    </div>
  );
}
