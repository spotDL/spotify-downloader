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
function entityTarget(entity: EntityEnvelope) {
  if (entity.type === "track" && entity.track) {
    return { trackId: entity.track.id, title: entity.track.name };
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
            toast.info(
              "That resolved to an album, artist, or playlist — those views land soon.",
            );
            return;
          }
          // Surface any degraded sources before leaving the page; a clean
          // resolve navigates straight through (CONTRACT — spec §6).
          if (res.degraded_sources.length > 0) {
            setDegraded({
              sources: res.degraded_sources,
              trackId: target.trackId,
              title: target.title,
            });
            return;
          }
          void goToTrack(target.trackId);
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
