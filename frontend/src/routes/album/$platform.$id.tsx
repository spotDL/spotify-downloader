import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useAlbum, useFindMatchesMutation } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { EntityHeader, TrackList } from "@/components/entity";
import { Card, CardContent, Spinner } from "@/components/ui";
import { features } from "@/config";
import type { Song } from "@/types";

export const Route = createFileRoute("/album/$platform/$id" as const)({
  component: AlbumPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function AlbumPage() {
  const navigate = useNavigate();
  const { platform, id } = Route.useParams();
  const { data: album, isLoading, error } = useAlbum(platform, id);
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
    if (!features.canDownload || !album?.songs.length) {
      navigate({ to: "/queue" });
      return;
    }

    const songsWithMatches: Array<{ song: Song; matchUrl?: string }> = [];

    for (const track of album.songs) {
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
          type: "album",
          name: album.name,
          url: album.url,
        }
      );
      navigate({ to: "/queue" });
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-6">
        <Spinner size="lg" />
        <p className="text-zinc-400">Loading album...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto border-red-900/50">
        <CardContent className="py-8 text-center">
          <p className="text-red-400">Failed to load album</p>
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

  if (!album) {
    return (
      <Card variant="bordered" className="max-w-2xl mx-auto">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-400">Album not found</p>
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
        <span className="text-zinc-300">{album.name}</span>
      </nav>

      {/* Header */}
      <EntityHeader
        type="album"
        name={album.name}
        platform={album.platform}
        imageUrl={album.cover_url}
        subtitle={album.artist_name}
        metadata={{
          year: album.year,
          totalTracks: album.total_tracks,
        }}
        onDownloadAll={features.canDownload ? handleDownloadAll : undefined}
        isDownloading={findMatchesMutation.isPending}
      />

      {/* Tracklist */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-100">Tracklist</h2>
        <Card variant="bordered">
          <TrackList
            tracks={album.songs}
            onDownload={features.canDownload ? handleDownloadTrack : undefined}
            showAlbum={false}
            showTrackNumber={true}
          />
        </Card>
      </div>
    </div>
  );
}
