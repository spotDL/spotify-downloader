import { useNavigate } from "@tanstack/react-router";
import { useResolve } from "../api/queries";
import { reportError } from "./report-error";

// Resolve-on-open (CONTRACT — spec §6). A search / command-palette hit is a
// provider snapshot preview, NOT a canonical entity: its `id` is a snapshot id
// (album/artist) or a bare provider ref (playlist), so navigating to the detail
// route directly 404s. Every hit carries `provider` + `provider_id`, so we POST
// `{provider}:{kind}:{provider_id}` to /resolve to obtain the canonical id the
// detail route reads, then navigate. Shared by the search screen + palette.

type EntityRef = {
  provider?: string | null;
  provider_id?: string | null;
};

type Kind = "track" | "album" | "artist" | "playlist";

export function useOpenEntity() {
  const navigate = useNavigate();
  const resolve = useResolve();

  const open = (kind: Kind, ref: EntityRef) => {
    if (!ref.provider || !ref.provider_id) {
      reportError(null, "That result can't be opened (no source reference).");
      return;
    }
    resolve.mutate(
      { body: { query: `${ref.provider}:${kind}:${ref.provider_id}` } },
      {
        onSuccess: (res) => {
          const e = res.entity;
          switch (e.type) {
            case "track":
              if (e.track) void navigate({ to: "/tracks/$trackId", params: { trackId: e.track.id } });
              break;
            case "album":
              if (e.album) void navigate({ to: "/albums/$albumId", params: { albumId: e.album.id } });
              break;
            case "artist":
              if (e.artist) void navigate({ to: "/artists/$artistId", params: { artistId: e.artist.id } });
              break;
            case "playlist":
              if (e.playlist)
                void navigate({ to: "/playlists/$playlistId", params: { playlistId: e.playlist.id } });
              break;
          }
        },
        onError: (err) => reportError(err, "Couldn't open that result."),
      },
    );
  };

  return {
    openTrack: (t: EntityRef) => open("track", t),
    openAlbum: (a: EntityRef) => open("album", a),
    openArtist: (a: EntityRef) => open("artist", a),
    openPlaylist: (p: EntityRef) => open("playlist", p),
    resolving: resolve.isPending,
  };
}
