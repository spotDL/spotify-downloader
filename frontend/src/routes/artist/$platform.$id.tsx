import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useArtist, useFindMatchesMutation } from "@/api";
import { useQueueStore } from "@/stores/queue";
import { EntityHeader, TrackList } from "@/components/entity";
import { Card, CardContent, Spinner } from "@/components/ui";
import { features } from "@/config";
import type { Song } from "@/types";

export const Route = createFileRoute("/artist/$platform/$id" as const)({
  component: ArtistPage,
});

const TARGET_PLATFORMS = ["youtube", "youtube_music", "soundcloud", "bandcamp"];

function ArtistPage() {
  const navigate = useNavigate();
  const { platform, id } = Route.useParams();
  const { data: artist, isLoading, error } = useArtist(platform, id);
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
    if (!features.canDownload || !artist?.songs.length) {
      navigate({ to: "/queue" });
      return;
    }

    // Add all tracks to queue with entity context
    const songsWithMatches: Array<{ song: Song; matchUrl?: string }> = [];

    for (const track of artist.songs) {
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
          type: "artist",
          name: artist.name,
          url: artist.url,
        }
      );
      navigate({ to: "/queue" });
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
            Back to search
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
        <span className="text-zinc-300">{artist.name}</span>
      </nav>

      {/* Header */}
      <EntityHeader
        type="artist"
        name={artist.name}
        platform={artist.platform}
        imageUrl={artist.image_url}
        metadata={{
          genres: artist.genres,
          totalTracks: artist.total_songs,
          followers: artist.followers,
        }}
        onDownloadAll={features.canDownload ? handleDownloadAll : undefined}
        isDownloading={findMatchesMutation.isPending}
      />

      {/* Discography */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-100">Discography</h2>
        <Card variant="bordered">
          <TrackList
            tracks={artist.songs}
            onDownload={features.canDownload ? handleDownloadTrack : undefined}
            showAlbum={true}
            showTrackNumber={false}
          />
        </Card>
      </div>
    </div>
  );
}
