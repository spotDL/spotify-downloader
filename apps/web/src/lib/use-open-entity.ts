import { useNavigate } from "@tanstack/react-router";
import { useResolve } from "../api/queries";
import { reportError } from "./report-error";

// Resolve-on-open (CONTRACT — spec §6). A search hit is a provider snapshot, not
// a canonical entity: a track ref must be POSTed to /resolve to obtain its
// canonical id before the /tracks/{id} route can serve it. Album/artist/playlist
// previews already carry the id their detail route reads, so they navigate
// directly. Shared by the search screen and the command palette.

type TrackRef = {
  id: string;
  provider?: string | null;
  provider_id?: string | null;
};

export function useOpenEntity() {
  const navigate = useNavigate();
  const resolve = useResolve();

  const openTrack = (track: TrackRef) => {
    if (!track.provider || !track.provider_id) {
      reportError(null, "That result can't be opened (no source reference).");
      return;
    }
    resolve.mutate(
      { body: { query: `${track.provider}:track:${track.provider_id}` } },
      {
        onSuccess: (res) => {
          const id = res.entity.type === "track" ? res.entity.track?.id : undefined;
          if (id) void navigate({ to: "/tracks/$trackId", params: { trackId: id } });
        },
        onError: (err) => reportError(err, "Couldn't open that result."),
      },
    );
  };

  const openAlbum = (id: string) =>
    void navigate({ to: "/albums/$albumId", params: { albumId: id } });
  const openArtist = (id: string) =>
    void navigate({ to: "/artists/$artistId", params: { artistId: id } });
  const openPlaylist = (id: string) =>
    void navigate({ to: "/playlists/$playlistId", params: { playlistId: id } });

  return {
    openTrack,
    openAlbum,
    openArtist,
    openPlaylist,
    resolving: resolve.isPending,
  };
}
