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
import { SearchIcon } from "../components/icons";
import { useUiStore } from "../stores/ui";

export const Route = createFileRoute("/")({
  component: Home,
});

// Navigation target for a resolved entity.
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

const HINTS = ["Spotify URL", "YouTube URL", "Artist - Song"];

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
  const recent = useUiStore((s) => s.recentSearches);
  const clearRecent = useUiStore((s) => s.clearRecentSearches);

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
    <div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col justify-center gap-8 px-6 py-12">
      <section className="animate-rise flex flex-col items-center gap-3 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-fg">
          spot<span className="text-emerald">DL</span>
        </h1>
        <p className="max-w-md text-muted">
          Search for a track, album, artist, or playlist — or paste a link.
        </p>
      </section>

      <div className="flex flex-col gap-4">
        <form
          role="search"
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            const next = query.trim();
            if (next.length > 0) void navigate({ to: "/search", search: { q: next } });
          }}
        >
          <div className="relative flex-1">
            <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-muted" />
            <Input
              type="search"
              aria-label="Search"
              placeholder="e.g. Daft Punk — Get Lucky"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-12 rounded-card pl-11 text-base"
            />
          </div>
          <Button
            type="submit"
            className="h-12 rounded-card px-6 text-base font-semibold"
          >
            Search
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-muted">
            Accepts
          </span>
          {HINTS.map((hint) => (
            <span
              key={hint}
              className="rounded-full border border-line-soft bg-elevated px-2.5 py-1 font-mono text-[11px] text-ink-2"
            >
              {hint}
            </span>
          ))}
        </div>
      </div>

      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={onResolve}>
        <Input
          type="text"
          aria-label="Paste a link"
          placeholder="Paste a Spotify or other supported link…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" variant="secondary" disabled={resolve.isPending}>
          {resolve.isPending ? <Spinner label="Opening" /> : "Open"}
        </Button>
      </form>

      {recent.length > 0 ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wide text-muted">
              Recent searches
            </span>
            <button
              type="button"
              onClick={clearRecent}
              className="font-mono text-[11px] text-muted hover:text-fg"
            >
              clear
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {recent.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => void navigate({ to: "/search", search: { q: r } })}
                className="rounded-full border border-line-soft bg-elevated px-3 py-1.5 text-sm text-ink-2 transition-colors hover:bg-hover hover:text-fg"
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      ) : null}

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
