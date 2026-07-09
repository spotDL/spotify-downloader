import { createFileRoute } from "@tanstack/react-router";
import { useAlbum } from "../api/queries";
import { CollectionView } from "../components/CollectionView";
import { joinMeta } from "../lib/format";

export const Route = createFileRoute("/albums/$albumId")({ component: AlbumPage });

function AlbumPage() {
  const { albumId } = Route.useParams();
  const query = useAlbum(albumId);
  return (
    <CollectionView
      query={query}
      toHeader={(album) => ({
        title: album.name,
        subtitle: album.album_artist,
        meta: joinMeta([
          album.year,
          album.track_count != null ? `${album.track_count} tracks` : null,
        ]),
        coverUrl: album.cover_url,
      })}
      toTracks={(album) => album.tracks ?? []}
      // Albums are a downloadable batch → Enqueue all (server expands to N jobs).
      enqueueQueryOf={(album) => album.id}
    />
  );
}
