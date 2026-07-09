import { createFileRoute } from "@tanstack/react-router";
import { usePlaylist } from "../api/queries";
import { CollectionView } from "../components/CollectionView";

export const Route = createFileRoute("/playlists/$playlistId")({
  component: PlaylistPage,
});

function PlaylistPage() {
  const { playlistId } = Route.useParams();
  const query = usePlaylist(playlistId);
  return (
    <CollectionView
      query={query}
      toHeader={(playlist) => ({
        title: playlist.name,
        subtitle: playlist.owner,
        meta: playlist.description,
        coverUrl: playlist.cover_url,
      })}
      toTracks={(playlist) => playlist.tracks ?? []}
      // Playlists are a downloadable batch → Enqueue all (server expands to N).
      enqueueQueryOf={(playlist) => playlist.id}
    />
  );
}
