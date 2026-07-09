import { createFileRoute } from "@tanstack/react-router";
import { useArtist } from "../api/queries";
import { CollectionView } from "../components/CollectionView";

export const Route = createFileRoute("/artists/$artistId")({
  component: ArtistPage,
});

function ArtistPage() {
  const { artistId } = Route.useParams();
  const query = useArtist(artistId);
  return (
    <CollectionView
      query={query}
      toHeader={(artist) => ({
        title: artist.name,
        subtitle:
          artist.genres && artist.genres.length > 0
            ? artist.genres.join(", ")
            : undefined,
        coverUrl: artist.image_url,
      })}
      toTracks={(artist) => artist.tracks ?? []}
      // No `enqueueQueryOf`: an artist is NOT a downloadable batch (Plan 8's
      // `unsupported_entity` rule). Enqueue is per-track via the track pages.
    />
  );
}
