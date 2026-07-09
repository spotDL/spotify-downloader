import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useResolve } from "../api/queries";
import type { EntityEnvelope } from "../api/generated/types.gen";
import { reportError } from "../lib/report-error";
import { toast } from "../components/Toasts";
import { Button } from "../components/Button";
import { DegradedBanner } from "../components/DegradedBanner";
import { Input } from "../components/Input";
import { Spinner } from "../components/Spinner";

export const Route = createFileRoute("/")({
  component: Home,
});

// Navigation target for a resolved entity. Only the track route exists in this
// track's scope; album/artist/playlist pages land in Task 8, so those types
// surface a placeholder toast until their routes are integrated.
// MERGE: extend to /albums, /artists, /playlists once those routes exist.
type ResolveTarget =
  | { kind: "track"; trackId: string; title: string }
  | { kind: "album" | "artist" | "playlist"; id: string; title: string };

function entityTarget(entity: EntityEnvelope): ResolveTarget | null {
  if (entity.type === "track" && entity.track) {
    return { kind: "track", trackId: entity.track.id, title: entity.track.name };
  }
  if (entity.type === "album" && entity.album) {
    return { kind: "album", id: entity.album.id, title: entity.album.name };
  }
  if (entity.type === "artist" && entity.artist) {
    return { kind: "artist", id: entity.artist.id, title: entity.artist.name };
  }
  if (entity.type === "playlist" && entity.playlist) {
    return { kind: "playlist", id: entity.playlist.id, title: entity.playlist.name };
  }
  return null;
}

function Home() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [degraded, setDegraded] = useState<{
    sources: string[];
    trackId: string;
    title: string;
  } | null>(null);

  const resolve = useResolve();

  const goToTrack = (trackId: string) =>
    navigate({ to: "/tracks/$trackId", params: { trackId } });

  const goToTarget = (target: ResolveTarget) => {
    if (target.kind === "track") return goToTrack(target.trackId);
    if (target.kind === "album")
      return navigate({ to: "/albums/$albumId", params: { albumId: target.id } });
    if (target.kind === "artist")
      return navigate({ to: "/artists/$artistId", params: { artistId: target.id } });
    return navigate({ to: "/playlists/$playlistId", params: { playlistId: target.id } });
  };

  const onResolve = (e: React.FormEvent) => {
    e.preventDefault();
    const value = url.trim();
    if (value.length === 0) return;
    setDegraded(null);
    resolve.mutate(
      { body: { query: value } },
      {
        onSuccess: (res) => {
          const target = entityTarget(res.entity);
          if (!target) {
            toast.info("That link resolved to something spotDL can't display yet.");
            return;
          }
          // Surface any degraded sources before leaving the page; a clean
          // resolve navigates straight through (CONTRACT — spec §6). The
          // banner's continue button only supports tracks; other kinds
          // navigate directly (their pages render their own degraded state).
          if (res.degraded_sources.length > 0 && target.kind === "track") {
            setDegraded({
              sources: res.degraded_sources,
              trackId: target.trackId,
              title: target.title,
            });
            return;
          }
          void goToTarget(target);
        },
        onError: (err) => reportError(err, "Couldn't open that link."),
      },
    );
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8 py-8">
      <section className="flex flex-col gap-2 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-fg">spotDL</h1>
        <p className="text-muted">
          Search for a track, album, artist, or playlist — or paste a link.
        </p>
      </section>

      <form
        role="search"
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const next = query.trim();
          if (next.length > 0) void navigate({ to: "/search", search: { q: next } });
        }}
      >
        <Input
          type="search"
          aria-label="Search"
          placeholder="e.g. Daft Punk — Get Lucky"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="submit">Search</Button>
      </form>

      <form className="flex gap-2" onSubmit={onResolve}>
        <Input
          type="text"
          aria-label="Paste a link"
          placeholder="Paste a Spotify or other supported link…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Button type="submit" variant="secondary" disabled={resolve.isPending}>
          {resolve.isPending ? <Spinner label="Opening" /> : "Open"}
        </Button>
      </form>

      {degraded ? (
        <div className="flex flex-col gap-3">
          <DegradedBanner sources={degraded.sources} />
          <div className="flex justify-end">
            <Button onClick={() => void goToTrack(degraded.trackId)}>
              Continue to “{degraded.title}”
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
